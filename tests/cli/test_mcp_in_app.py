import asyncio
from pathlib import Path

from doubles import until
from mcp import Client
from mcp.types import CallToolResult
from mcp_doubles import (
    MATERIA_ID,
    PROVA_ID,
    ScriptedAgendamentos,
    answer_of,
    error_of,
    uninter_server,
)
from textual.app import App

from api.materias.entity import Materia
from api.mcp_server.http import McpListener
from cli.mcp_host import AppHost
from cli.pages.agendar.page import ConfirmBooking

SIZE = (100, 30)
BOOK_PATH = "POST /ava/pap/AgendamentoUsuario"


class HostApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.refreshed: list[int] = []

    def refresh_materia(self, materia: Materia) -> None:
        self.refreshed.append(materia.id)


async def book_over_http(url: str) -> CallToolResult:
    async with Client(url) as client:
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


async def test_sim_in_the_app_books_what_the_client_asked(tmp_path: Path) -> None:
    app = HostApp()
    host = AppHost(app, app.refresh_materia)
    ava = ScriptedAgendamentos()
    listener = McpListener.bind("127.0.0.1", 0)
    async with (
        uninter_server(tmp_path, lambda ctx: host, ava) as server,
        listener.serving(server),
    ):
        asked = asyncio.ensure_future(book_over_http(listener.url))
        async with app.run_test(size=SIZE) as pilot:
            await until(pilot, lambda: isinstance(app.screen, ConfirmBooking))
            await pilot.press("right")
            await pilot.press("enter")
            result = await asked
            await until(pilot, lambda: app.refreshed == [MATERIA_ID])

    assert not result.is_error
    assert ava.sent == [BOOK_PATH]


async def test_closing_the_app_refuses_what_is_waiting(tmp_path: Path) -> None:
    app = HostApp()
    host = AppHost(app, app.refresh_materia)
    ava = ScriptedAgendamentos()
    listener = McpListener.bind("127.0.0.1", 0)
    async with (
        uninter_server(tmp_path, lambda ctx: host, ava) as server,
        listener.serving(server),
    ):
        asked = asyncio.ensure_future(book_over_http(listener.url))
        async with app.run_test(size=SIZE) as pilot:
            await until(pilot, lambda: isinstance(app.screen, ConfirmBooking))
        host.close()
        result = await asked

    assert "Recusado no app: o app fechou antes da resposta" in error_of(result)
    assert ava.sent == []
