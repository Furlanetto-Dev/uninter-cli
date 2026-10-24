import socket
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

import httpx
from doubles import SettingsWithoutEnvFile
from factories import make_materia
from mcp import Client
from mcp.client.session import ClientRequestContext, ElicitationFnT
from mcp.types import CallToolResult, ElicitRequestParams, ElicitResult
from mcp_doubles import (
    MATERIA_ID,
    PROVA_ID,
    ScriptedAgendamentos,
    answer_of,
    error_of,
    mcp_client,
)

from api.aulas.entity import Aula, AulaAtividade, Material
from api.db import db_session
from api.materias.entity import Materia
from api.mcp_server.elicit import AppAddress, ElicitHost
from api.mcp_server.tools import HostOf, McpContext
from config import Config
from mcp_stdio import stdio_server

BOOK_PATH = "POST /ava/pap/AgendamentoUsuario"
APP_URL = "http://127.0.0.1:{port}/mcp"
AULA_ID = 6
ROTA = "https://conteudosdigitais.uninter.com/libraries/newrota/?c=/gradNova/2022/ads/poo/a1&amp;hash=abc"
INDEX = "https://conteudosdigitais.uninter.com/materiais/aulas/gradNova/2022/ads/poo/a1/index.json"
VIDEO = "https://vod.grupouninter.com.br/2022/JUN/poo-A01-P01"
VTT = "WEBVTT\r\n\r\n0:00:01.000 --> 0:00:02.000\r\nFala da conversa inicial.\r\n"

Action = Literal["accept", "decline", "cancel"]


class Refreshes:
    def __init__(self) -> None:
        self.materias: list[int] = []

    async def __call__(self, materia: Materia) -> None:
        self.materias.append(materia.id)


@contextmanager
def a_port(*, listening: bool) -> Generator[int]:
    with socket.socket() as bound:
        bound.bind(("127.0.0.1", 0))
        if listening:
            bound.listen()
        yield bound.getsockname()[1]


def stdio_host(port: int, refreshes: Refreshes) -> HostOf:
    address = AppAddress("127.0.0.1", port, APP_URL.format(port=port))

    def host_of(ctx: McpContext) -> ElicitHost:
        return ElicitHost(ctx, address, refreshes)

    return host_of


def student_answers(action: Action, confirmar: bool = True) -> ElicitationFnT:
    async def answer(
        context: ClientRequestContext, params: ElicitRequestParams
    ) -> ElicitResult:
        if action == "accept":
            return ElicitResult(action=action, content={"confirmar": confirmar})
        return ElicitResult(action=action)

    return answer


async def book_first_horario(client: Client) -> CallToolResult:
    horarios = answer_of(
        await client.call_tool(
            "list_horarios", {"materia_id": MATERIA_ID, "atividade_id": PROVA_ID}
        )
    )
    return await client.call_tool(
        "book_prova",
        {
            "materia_id": MATERIA_ID,
            "atividade_id": PROVA_ID,
            "laboratorio_id": horarios[0]["laboratorio_id"],
            "inicio": horarios[0]["inicio"],
        },
    )


async def test_a_client_without_elicitation_gets_the_action_refused(
    tmp_path: Path,
) -> None:
    ava = ScriptedAgendamentos()
    with a_port(listening=False) as port:
        async with mcp_client(tmp_path, stdio_host(port, Refreshes()), ava) as client:
            result = await book_first_horario(client)

    assert "Recusado no cliente: este cliente não sabe pedir confirmação" in error_of(
        result
    )
    assert ava.sent == []


async def test_confirming_through_elicitation_books_and_refreshes(
    tmp_path: Path,
) -> None:
    ava = ScriptedAgendamentos()
    refreshes = Refreshes()
    with a_port(listening=False) as port:
        async with mcp_client(
            tmp_path,
            stdio_host(port, refreshes),
            ava,
            elicitation_callback=student_answers("accept"),
        ) as client:
            result = await book_first_horario(client)

    assert not result.is_error
    assert ava.sent == [BOOK_PATH]
    assert refreshes.materias == [MATERIA_ID]


async def test_leaving_confirmar_unchecked_books_nothing(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    with a_port(listening=False) as port:
        async with mcp_client(
            tmp_path,
            stdio_host(port, Refreshes()),
            ava,
            elicitation_callback=student_answers("accept", confirmar=False),
        ) as client:
            result = await book_first_horario(client)

    assert "Recusado no cliente: o aluno recusou" in error_of(result)
    assert ava.sent == []


async def test_cancelling_the_question_books_nothing(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    with a_port(listening=False) as port:
        async with mcp_client(
            tmp_path,
            stdio_host(port, Refreshes()),
            ava,
            elicitation_callback=student_answers("cancel"),
        ) as client:
            result = await book_first_horario(client)

    assert "Recusado no cliente: o aluno cancelou" in error_of(result)
    assert ava.sent == []


async def test_an_open_app_keeps_stdio_away_from_the_ava(tmp_path: Path) -> None:
    ava = ScriptedAgendamentos()
    with a_port(listening=True) as port:
        async with mcp_client(tmp_path, stdio_host(port, Refreshes()), ava) as client:
            result = await client.call_tool(
                "list_horarios", {"materia_id": MATERIA_ID, "atividade_id": PROVA_ID}
            )

    assert APP_URL.format(port=port) in error_of(result)
    assert ava.paths == []


async def test_reads_work_while_the_app_is_open(tmp_path: Path) -> None:
    with a_port(listening=True) as port:
        async with mcp_client(
            tmp_path, stdio_host(port, Refreshes()), ScriptedAgendamentos()
        ) as client:
            result = await client.call_tool("list_materias", {})

    assert not result.is_error


def public_cdn(request: httpx.Request) -> httpx.Response:
    if str(request.url) == INDEX:
        midia = {"1": {"titulo": "Conversa Inicial", "url": f"{VIDEO}.mp4"}}
        return httpx.Response(200, json={"aula": {"midia": midia}})
    if str(request.url) == f"{VIDEO}_pt_BR.vtt":
        return httpx.Response(200, text=VTT)
    return httpx.Response(404)


async def seed_aula_with_rota(database: Path) -> None:
    async with db_session(database) as session:
        session.add(make_materia(materia_id=MATERIA_ID))
        session.add(
            Aula(
                materia_id=MATERIA_ID,
                id=AULA_ID,
                nome="Exceções",
                ordem=6,
                estrutura="Aula 6",
            )
        )
        session.add(
            AulaAtividade(aula_id=AULA_ID, id=61, nome="Teórica", tipo="Rota", ordem=1)
        )
        session.add(
            Material(atividade_id=61, id=611, tipo="rota", acao="Iniciar", url=ROTA)
        )
        await session.commit()


async def test_dev_mode_still_reads_transcricoes_from_the_public_cdn(
    tmp_path: Path,
) -> None:
    database = tmp_path / "uninter.db"
    await seed_aula_with_rota(database)
    async with (
        stdio_server(
            SettingsWithoutEnvFile(),
            Config(dev_mode=True),
            lambda: httpx.MockTransport(public_cdn),
            database,
        ) as server,
        Client(server) as client,
    ):
        result = await client.call_tool(
            "get_transcricoes", {"materia_id": MATERIA_ID, "aula_id": AULA_ID}
        )

    assert [item["texto"] for item in answer_of(result)] == [
        "Fala da conversa inicial."
    ]
