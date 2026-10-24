import asyncio
import contextlib
from collections.abc import AsyncGenerator, Callable
from pathlib import Path

import httpx
from mcp.server.mcpserver import MCPServer
from sqlalchemy.ext.asyncio import AsyncEngine

from api.agendamentos.repository import AgendamentoRepository
from api.agendamentos.service import AgendamentoService
from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.credenciais.startup import from_env, stored
from api.db import DATABASE_PATH, db_engine, open_session
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from api.mcp_server.elicit import AppAddress, ElicitHost
from api.mcp_server.http import MCP_PATH
from api.mcp_server.tools import McpContext, Sources, build_server
from api.mcp_server.transcricoes import transcricoes_from_cdn
from api.mock import aulas, fixture
from api.mock.offline import NoSession, OfflineLogin
from config import Config
from crawler.agendamentos.request import AgendamentoRequest
from crawler.atividades.request import AtividadeRequest
from crawler.credenciais import NotLoggedIn
from crawler.history import RequestLog
from crawler.mock import FakeAva
from crawler.session import (
    AvaSession,
    AvaUnreachable,
    LoginRejected,
    ava_client,
    public_client,
)
from settings import Settings

REFRESH_FAILURES = (
    httpx.HTTPError,
    AvaUnreachable,
    LoginRejected,
    NotLoggedIn,
    ValueError,
)


Internet = Callable[[], httpx.AsyncBaseTransport]


def fake_ava(mocked: fixture.MockedAva, real: httpx.AsyncBaseTransport) -> FakeAva:
    return FakeAva(mocked.payload, fixture.figure, aulas.transcricao, real)


def ava_transport(
    config: Config, mocked: fixture.MockedAva, internet: Internet
) -> httpx.AsyncBaseTransport:
    if config.dev_mode:
        return OfflineLogin(fake_ava(mocked, NoSession()))
    return fake_ava(mocked, internet())


def app_address(settings: Settings) -> AppAddress:
    url = f"http://{settings.mcp_host}:{settings.mcp_port}{MCP_PATH}"
    return AppAddress(settings.mcp_host, settings.mcp_port, url)


class AtividadesRefresh:
    def __init__(
        self, engine: AsyncEngine, ava: AvaSession, agendamentos: AgendamentoService
    ) -> None:
        self._engine = engine
        self._request = AtividadeRequest(ava)
        self._agendamentos = agendamentos

    async def __call__(self, materia: Materia) -> None:
        async with open_session(self._engine) as session:
            service = AtividadeSyncService(
                session=session,
                request=self._request,
                repository=AtividadeRepository(session),
                materias=MateriaRepository(session),
                capturas=CapturaRepository(session),
                agendamentos=self._agendamentos,
                agendamentos_db=AgendamentoRepository(session),
            )
            with contextlib.suppress(*REFRESH_FAILURES):
                await service.sync(materia)


@contextlib.asynccontextmanager
async def stdio_server(
    settings: Settings,
    config: Config,
    internet: Internet = httpx.AsyncHTTPTransport,
    database: Path = DATABASE_PATH,
) -> AsyncGenerator[MCPServer]:
    log = RequestLog()
    mocked = fixture.MockedAva()
    async with (
        ava_client(ava_transport(config, mocked, internet), log) as http,
        public_client(fake_ava(mocked, internet()), log) as public_http,
        db_engine(database) as engine,
    ):
        async with open_session(engine) as session:
            credenciais = await stored(
                from_env(settings), CredencialRepository(session)
            )
        ava = AvaSession(http, credenciais, log)
        agendamentos = AgendamentoService(AgendamentoRequest(ava))
        refresh = AtividadesRefresh(engine, ava, agendamentos)
        address = app_address(settings)

        def host_of(ctx: McpContext) -> ElicitHost:
            return ElicitHost(ctx, address, refresh)

        yield build_server(
            Sources(engine, agendamentos, transcricoes_from_cdn(public_http)),
            host_of,
        )


async def serve_stdio() -> None:
    settings = Settings.model_validate({})
    async with stdio_server(settings, Config.load()) as server:
        await server.run_stdio_async()


if __name__ == "__main__":
    asyncio.run(serve_stdio())
