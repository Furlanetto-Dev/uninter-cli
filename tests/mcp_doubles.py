from collections.abc import AsyncGenerator, Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from factories import make_atividade, make_materia
from mcp import Client
from mcp.server.mcpserver import MCPServer
from mcp.client.session import ElicitationFnT
from mcp.types import CallToolResult
from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.service import AgendamentoService
from api.atividades.entity import Atividade
from api.atividades.repository import AtividadeRepository
from api.aulas.entity import Aula
from api.db import db_engine, open_session
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.mcp_server.host import Booking, Cancelling, Host, Recusa, ScreenRefused
from api.mcp_server.tools import HostOf, Sources, build_server
from api.mcp_server.transcricoes import TranscricaoLike, TranscricaoSource
from api.mcp_server.views import (
    AtividadeOnScreenView,
    CurrentScreenView,
    MateriaOnScreenView,
    OpenProvaView,
    ProvaOnScreenView,
    QuestaoOfProvaView,
    QuestaoOnScreenView,
)
from api.mock.agendamentos import MockedAgendamentos
from crawler.agendamentos.request import AgendamentoRequest
from crawler.credenciais import Credenciais
from crawler.session import LOGIN_PATH, AvaSession, ava_client

OFERTA = 899_306
MATERIA_ID = 1
PROVA_ID = 2_523_475
PROVA = "Prova Objetiva (Regular)"
LOGGED_IN = {
    "usuario": {
        "nome": "Aluno",
        "time": "639282711628924280",
        "idUsuario": 3_316_075,
        "idGrupoEstrutura": 339,
    }
}
FORM_METHODS = ("POST", "PUT")

Seed = Callable[[AsyncSession], Awaitable[None]]


def banco_de_dados() -> Materia:
    return make_materia(
        materia_id=MATERIA_ID, nome="Banco de Dados", oferta_atual=OFERTA
    )


def presencial_prova(*, fim: datetime | None = None) -> Atividade:
    return make_atividade(
        atividade_id=PROVA_ID,
        materia_id=MATERIA_ID,
        nome=PROVA,
        tipo="Prova",
        presencial=True,
        peso=60,
        fim=fim or datetime.now() + timedelta(days=10),
    )


def apol() -> Atividade:
    return make_atividade(
        atividade_id=11,
        materia_id=MATERIA_ID,
        nome="APOL 1",
        peso=40,
        contribuicao=36.0,
    )


async def seed_banco_de_dados(session: AsyncSession) -> None:
    materia = banco_de_dados()
    materias = MateriaRepository(session)
    await materias.save([materia])
    await materias.mark_atividades_synced(materia)
    await AtividadeRepository(session).replace(materia, [apol(), presencial_prova()])
    await session.commit()


class ScriptedAgendamentos:
    def __init__(self, *, refusing_session: bool = False) -> None:
        self._mock = MockedAgendamentos(OFERTA, {PROVA_ID: PROVA})
        self._refusing_session = refusing_session
        self.paths: list[str] = []
        self.sent: list[str] = []

    def answer(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith(LOGIN_PATH):
            return httpx.Response(200, json=LOGGED_IN)
        self.paths.append(path)
        if self._refusing_session:
            return httpx.Response(401)
        payload = self._mock.payload(str(request.url), request.content.decode())
        if payload is None:
            return httpx.Response(404)
        if request.method in FORM_METHODS:
            self.sent.append(f"{request.method} {path}")
        return httpx.Response(200, json=payload)


PROVA_ON_SCREEN = CurrentScreenView(
    page="prova",
    materia=MateriaOnScreenView(id=MATERIA_ID, nome="Banco de Dados", periodo="2026/1"),
    prova=ProvaOnScreenView(
        atividade=AtividadeOnScreenView(id=PROVA_ID, nome="Prova Objetiva"),
        questao=QuestaoOnScreenView(
            ordem=2,
            total=10,
            enunciado="Qual forma normal elimina dependências parciais?",
            alternativas=["a) 1FN", "b) 2FN"],
            alternativa_marcada="b",
        ),
        respostas=["1: a) Sim", "2: b) 2FN"],
        entregue=False,
    ),
)

OPEN_PROVA = OpenProvaView(
    materia=MateriaOnScreenView(id=MATERIA_ID, nome="Banco de Dados", periodo="2026/1"),
    atividade=AtividadeOnScreenView(id=PROVA_ID, nome="Prova Objetiva"),
    questao_aberta=2,
    entregue=False,
    questoes=[
        QuestaoOfProvaView(
            ordem=ordem,
            enunciado=f"Enunciado {ordem}",
            comando="Assinale a correta",
            alternativas=["a) 1FN", "b) 2FN"],
            alternativa_marcada="b" if ordem == 1 else None,
        )
        for ordem in (1, 2, 3)
    ],
)


@dataclass
class FakeHost:
    answer: Recusa | None = None
    asked: list[Booking | Cancelling] = field(default_factory=lambda: [])
    refreshed: list[int] = field(default_factory=lambda: [])
    screen: CurrentScreenView | None = None
    prova: OpenProvaView | None = None
    refusal: str | None = None
    navigated: list[str] = field(default_factory=lambda: [])

    async def claim_ava(self) -> None:
        return None

    async def confirm_booking(self, booking: Booking) -> Recusa | None:
        self.asked.append(booking)
        return self.answer

    async def confirm_cancelling(self, cancelling: Cancelling) -> Recusa | None:
        self.asked.append(cancelling)
        return self.answer

    async def refresh(self, materia: Materia) -> None:
        self.refreshed.append(materia.id)

    def current_screen(self) -> CurrentScreenView | None:
        return self.screen

    def open_prova(self) -> OpenProvaView:
        if self.prova is None:
            raise ScreenRefused("não há prova aberta no app")
        return self.prova

    async def open_materia(self, materia_id: int, tab: str) -> CurrentScreenView:
        return self._navigated(f"open_materia {materia_id} {tab}")

    async def open_questao(self, numero: int) -> CurrentScreenView:
        return self._navigated(f"open_questao {numero}")

    async def go_back(self) -> CurrentScreenView:
        return self._navigated("go_back")

    async def read_screen(self) -> str:
        return self._navigated("read_screen").page

    def _navigated(self, action: str) -> CurrentScreenView:
        if self.refusal is not None:
            raise ScreenRefused(self.refusal)
        self.navigated.append(action)
        return self.screen or CurrentScreenView(page="nenhuma")


@dataclass(frozen=True)
class Transcricao:
    material_id: int
    ordem: int
    titulo: str
    texto: str
    buscada_em: datetime


class FakeTranscricoes:
    def __init__(
        self, transcricoes: Sequence[Transcricao] = (), failure: Exception | None = None
    ) -> None:
        self._transcricoes = transcricoes
        self._failure = failure
        self.asked: list[int] = []

    def __call__(self, session: AsyncSession) -> TranscricaoSource:
        return self

    async def of_aula(self, aula: Aula) -> Sequence[TranscricaoLike]:
        self.asked.append(aula.id)
        if self._failure is not None:
            raise self._failure
        return self._transcricoes


def fixed_host(host: Host) -> HostOf:
    return lambda ctx: host


@asynccontextmanager
async def uninter_server(
    tmp_path: Path,
    host_of: HostOf,
    ava: ScriptedAgendamentos,
    *,
    seed: Seed = seed_banco_de_dados,
    transcricoes: FakeTranscricoes | None = None,
) -> AsyncGenerator[MCPServer]:
    async with (
        db_engine(tmp_path / "uninter.db") as engine,
        ava_client(httpx.MockTransport(ava.answer)) as http,
    ):
        async with open_session(engine) as session:
            await seed(session)
        session_ava = AvaSession(http, Credenciais("1234567", "segredo"))
        sources = Sources(
            engine,
            AgendamentoService(AgendamentoRequest(session_ava)),
            transcricoes or FakeTranscricoes(),
        )
        yield build_server(sources, host_of)


@asynccontextmanager
async def mcp_client(
    tmp_path: Path,
    host_of: HostOf,
    ava: ScriptedAgendamentos,
    *,
    seed: Seed = seed_banco_de_dados,
    transcricoes: FakeTranscricoes | None = None,
    elicitation_callback: ElicitationFnT | None = None,
) -> AsyncGenerator[Client]:
    mode: Any = "legacy" if elicitation_callback is not None else "auto"
    async with (
        uninter_server(
            tmp_path, host_of, ava, seed=seed, transcricoes=transcricoes
        ) as server,
        Client(server, elicitation_callback=elicitation_callback, mode=mode) as client,
    ):
        yield client


def answer_of(result: CallToolResult) -> Any:
    assert not result.is_error, result.content
    structured: dict[str, Any] = result.structured_content or {}
    return structured.get("result", structured)


def error_of(result: CallToolResult) -> str:
    assert result.is_error
    return " ".join(getattr(block, "text", "") for block in result.content)
