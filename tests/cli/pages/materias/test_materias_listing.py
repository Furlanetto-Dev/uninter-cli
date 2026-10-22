from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
import pytest
from sqlmodel.ext.asyncio.session import AsyncSession
from textual.command import CommandPalette
from textual.pilot import Pilot
from textual.widgets import OptionList

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.aulas.arquivos import Arquivos
from api.aulas.repository import AulaRepository
from api.aulas.service import AulaSyncService
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.db import db_session
from api.gabaritos.repository import GabaritoRepository
from api.gabaritos.service import GabaritoService
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.mock.seed import MockedMateria
from api.provas.service import ProvaService
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from cli.app import UninterApp
from cli.pages.materias.components.list import MateriaList
from cli.pages.materias.components.table import TrabalhoTable
from cli.pages.materias.page import MateriasPage
from cli.pages.trabalho.page import TrabalhoPage
from config import Config
from crawler.atividades.gabarito import GabaritoRequest
from crawler.atividades.prova import AvaProvas
from crawler.atividades.request import AtividadeRequest
from crawler.aulas.request import (
    ArquivoRequest,
    AulaAtividadeRequest,
    AulaRequest,
    MaterialRequest,
)
from crawler.credenciais import Credenciais
from crawler.history import RequestLog
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession, ava_client
from crawler.trabalhos.request import EntregaRequest, EtiquetaRequest, TrabalhoRequest
from crawler.turmas.request import TurmaRequest
from doubles import make_figures, until, workers_finished
from factories import make_atividade, make_materia, make_trabalho

SIZE = (140, 45)
RU = "1234567"
SENHA = "segredo"
LOGIN_PATH = "/ava/autenticacao/autenticar/false/Post"
TURMAS_PATH = "/ava/sistema/Curso/0/EscolaUsuario/true/"
LISTING_PATH = "/ava/ava/SalaVirtual/6079/CursoUsuarioPermissao/true/"
ATIVIDADES_PATH = "/ava/bqs/AvaliacaoUsuario/1/paginacao/true"
LOGGED_IN = {"usuario": {"nome": "Aluno", "time": "639282711628924280"}}
TURMA = {
    "idCurso": 6079,
    "nome": "BACHARELADO EM ENGENHARIA DE SOFTWARE - DISTÂNCIA",
    "turma": "2025/02 GD ENGENHARIA DE SOFTWARE ",
}
ENGENHARIA: dict[str, object] = {
    "id": 1,
    "nome": "Engenharia de Software",
    "modulo": "2026/1 - UTA Engenharia de Software",
    "idSalaVirtualOfertaAtual": 511_000,
    "vigente": True,
}
BANCO: dict[str, object] = {
    "id": 2,
    "nome": "Banco de Dados",
    "modulo": "2026/1 - UTA Engenharia de Software",
    "idSalaVirtualOfertaAtual": 512_000,
    "vigente": True,
}

Answer = Callable[[httpx.Request], httpx.Response]


class ScriptedAva:
    def __init__(self, *materias: dict[str, object]) -> None:
        self.materias = list(materias)
        self.paths: list[str] = []
        self.listing: Answer = self.list_materias

    def list_materias(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"salaVirtuais": self.materias})

    def answer(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        self.paths.append(path)
        if path == LOGIN_PATH:
            return httpx.Response(200, json=LOGGED_IN)
        if path == TURMAS_PATH:
            return httpx.Response(200, json={"cursos": [TURMA]})
        if path == LISTING_PATH:
            return self.listing(request)
        return httpx.Response(404)

    @property
    def listings(self) -> int:
        return self.paths.count(LISTING_PATH)


def session_refused(request: httpx.Request) -> httpx.Response:
    return httpx.Response(401)


def network_down(request: httpx.Request) -> httpx.Response:
    raise httpx.ConnectError("sem rede", request=request)


async def seed_engenharia(session: AsyncSession) -> None:
    materia = make_materia(vigente=True)
    materias_db = MateriaRepository(session)
    await materias_db.save([materia])
    await materias_db.mark_atividades_synced(materia)
    await materias_db.mark_trabalhos_synced(materia)
    await materias_db.mark_aulas_synced(materia)
    await AtividadeRepository(session).replace(materia, [make_atividade()])
    await TrabalhoRepository(session).replace(materia, [make_trabalho()], [], [])
    await session.commit()


@asynccontextmanager
async def opened_app(
    tmp_path: Path, ava: ScriptedAva
) -> AsyncGenerator[tuple[UninterApp, Pilot[None]], None]:
    log = RequestLog()
    transport = httpx.MockTransport(ava.answer)
    async with (
        ava_client(transport, log) as http,
        db_session(tmp_path / "uninter.db") as session,
    ):
        await seed_engenharia(session)
        credenciais = Credenciais(RU, SENHA)
        session_ava = AvaSession(http, credenciais, log)
        materias_db = MateriaRepository(session)
        atividades_db = AtividadeRepository(session)
        trabalhos_db = TrabalhoRepository(session)
        aulas_db = AulaRepository(session)
        capturas_db = CapturaRepository(session)
        atividades_request = AtividadeRequest(session_ava)
        app = UninterApp(
            MateriaSyncService(
                session=session,
                ava=session_ava,
                request=MateriaRequest(session_ava, credenciais),
                repository=materias_db,
                capturas=capturas_db,
            ),
            AtividadeSyncService(
                session=session,
                request=atividades_request,
                repository=atividades_db,
                materias=materias_db,
                capturas=capturas_db,
            ),
            TrabalhoSyncService(
                session=session,
                trabalhos=TrabalhoRequest(session_ava),
                entregas=EntregaRequest(session_ava),
                etiquetas=EtiquetaRequest(session_ava),
                repository=trabalhos_db,
                materias=materias_db,
                capturas=capturas_db,
            ),
            AulaSyncService(
                session=session,
                aulas=AulaRequest(session_ava),
                atividades=AulaAtividadeRequest(session_ava),
                materiais=MaterialRequest(session_ava),
                repository=aulas_db,
                materias=materias_db,
                capturas=capturas_db,
            ),
            ProvaService(AvaProvas(session_ava), atividades_request),
            materias_db,
            atividades_db,
            trabalhos_db,
            aulas_db,
            capturas_db,
            GabaritoService(
                session=session,
                request=GabaritoRequest(session_ava),
                repository=GabaritoRepository(session),
            ),
            make_figures(),
            Arquivos(tmp_path / "arquivos", ArquivoRequest(http)),
            MockedMateria(session),
            Config.load(tmp_path / "config.json"),
            session_ava,
            TurmaRequest(session_ava),
            credenciais,
            CredencialRepository(session),
            log,
        )
        async with app.run_test(size=SIZE) as pilot:
            await until(pilot, lambda: ava.listings == 1)
            await workers_finished(app)
            yield app, pilot


def painted(widget: OptionList) -> str:
    return "\n".join(widget.render_line(row).text for row in range(widget.size.height))


def listed(app: UninterApp) -> str:
    return painted(app.screen.query_one(MateriaList))


async def visit_a_trabalho(app: UninterApp, pilot: Pilot[None]) -> None:
    await pilot.press("2")
    await pilot.press("right")
    await until(pilot, lambda: isinstance(app.focused, TrabalhoTable))
    await pilot.press("enter")
    await until(pilot, lambda: isinstance(app.screen, TrabalhoPage))
    await pilot.press("escape")
    await until(pilot, lambda: isinstance(app.screen, MateriasPage))


async def test_opening_the_app_sends_the_listing_once(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, _):
        await workers_finished(app)

        assert ava.listings == 1


async def test_coming_back_from_a_page_sends_the_listing_again(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        await visit_a_trabalho(app, pilot)
        await until(pilot, lambda: ava.listings == 2)

        assert ava.listings == 2


async def test_closing_the_command_palette_sends_nothing(tmp_path: Path) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        await pilot.press("ctrl+p")
        await until(pilot, lambda: isinstance(app.screen, CommandPalette))
        await pilot.press("escape")
        await until(pilot, lambda: isinstance(app.screen, MateriasPage))
        await pilot.pause(0.1)
        await workers_finished(app)

        assert ava.listings == 1


async def test_r_sends_the_listing_next_to_the_highlighted_materia(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (_, pilot):
        await pilot.press("r")
        await until(pilot, lambda: ATIVIDADES_PATH in ava.paths)
        await until(pilot, lambda: ava.listings == 2)

        assert ava.listings == 2


async def test_a_new_materia_shows_up_without_moving_the_student(
    tmp_path: Path,
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    async with opened_app(tmp_path, ava) as (app, pilot):
        ava.materias.append(BANCO)

        await visit_a_trabalho(app, pilot)
        await until(pilot, lambda: "Banco de Dados" in listed(app))

        assert isinstance(app.focused, TrabalhoTable)
        assert "Engenharia de Software" in listed(app)


@pytest.mark.parametrize(
    "failure", [session_refused, network_down], ids=["401", "no network"]
)
async def test_a_failed_listing_keeps_the_app_open(
    tmp_path: Path, failure: Answer
) -> None:
    ava = ScriptedAva(ENGENHARIA)
    ava.listing = failure
    async with opened_app(tmp_path, ava) as (app, _):
        await workers_finished(app)

        assert isinstance(app.screen, MateriasPage)
        assert "Engenharia de Software" in listed(app)
