import asyncio
import logging
import shutil
import sys

import httpx

from api.agendamentos.repository import AgendamentoRepository
from api.agendamentos.service import AgendamentoService
from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.aulas.arquivos import Arquivos
from api.aulas.repository import AulaRepository
from api.aulas.service import AulaSyncService
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.credenciais.startup import from_env, stored
from api.db import DATABASE_PATH, db_engine, open_session
from api.figures.repository import FigureRepository
from api.figures.service import FigureService
from api.gabaritos.repository import GabaritoRepository
from api.gabaritos.service import GabaritoService
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.mcp_server.http import McpListener, port_taken, serving
from api.mcp_server.tools import Sources, build_server
from api.mcp_server.transcricoes import transcricoes_from_cdn
from api.mock import aulas, fixture
from api.mock.seed import MockedMateria
from api.provas.service import ProvaService
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from cli.app import UninterApp
from cli.figures import Figures, painter
from cli.lib.claude.launchers import choose_launchers
from cli.lib.claude.opener import ClaudeTerminal, SystemShell
from cli.lib.claude.terminal import installed_claude
from config import Config
from crawler.agendamentos.request import AgendamentoRequest
from crawler.atividades.gabarito import GabaritoRequest
from crawler.atividades.prova import AvaProvas
from crawler.atividades.request import AtividadeRequest
from crawler.aulas.request import (
    ArquivoRequest,
    AulaAtividadeRequest,
    AulaRequest,
    MaterialRequest,
)
from crawler.figures.request import FigureRequest
from crawler.history import RequestLog
from crawler.materias.request import MateriaRequest
from crawler.mock import FakeAva
from crawler.session import AvaSession, ava_client, public_client
from crawler.trabalhos.request import EntregaRequest, EtiquetaRequest, TrabalhoRequest
from crawler.turmas.request import TurmaRequest
from settings import Settings, TerminalEnvironment


def listener_or_failure(settings: Settings) -> tuple[McpListener | None, str | None]:
    try:
        return McpListener.bind(settings.mcp_host, settings.mcp_port), None
    except OSError as error:
        return None, port_taken(settings.mcp_host, settings.mcp_port, error)


def fake_ava(mocked: fixture.MockedAva) -> FakeAva:
    return FakeAva(
        mocked.payload, fixture.figure, aulas.transcricao, httpx.AsyncHTTPTransport()
    )


async def run(settings: Settings) -> bool:
    log = RequestLog()
    mocked = fixture.MockedAva()
    listener, mcp_failure = listener_or_failure(settings)
    async with (
        ava_client(fake_ava(mocked), log) as http,
        public_client(fake_ava(mocked), log) as public_http,
        db_engine() as engine,
        open_session(engine) as session,
    ):
        credenciais_db = CredencialRepository(session)
        credenciais = await stored(from_env(settings), credenciais_db)
        ava = AvaSession(http, credenciais, log)
        materias_db = MateriaRepository(session)
        atividades_db = AtividadeRepository(session)
        trabalhos_db = TrabalhoRepository(session)
        aulas_db = AulaRepository(session)
        capturas_db = CapturaRepository(session)
        agendamentos_db = AgendamentoRepository(session)
        agendamentos_service = AgendamentoService(AgendamentoRequest(ava))
        gabaritos_service = GabaritoService(
            session=session,
            request=GabaritoRequest(ava),
            repository=GabaritoRepository(session),
        )
        figure_service = FigureService(
            session=session,
            request=FigureRequest(ava),
            repository=FigureRepository(session),
        )
        await figure_service.forget_stale()
        figures = Figures(figure_service, painter())
        materias_service = MateriaSyncService(
            session=session,
            ava=ava,
            request=MateriaRequest(ava, credenciais),
            repository=materias_db,
            capturas=capturas_db,
        )
        atividades_request = AtividadeRequest(ava)
        atividades_service = AtividadeSyncService(
            session=session,
            request=atividades_request,
            repository=atividades_db,
            materias=materias_db,
            capturas=capturas_db,
            agendamentos=agendamentos_service,
            agendamentos_db=agendamentos_db,
        )
        trabalhos_service = TrabalhoSyncService(
            session=session,
            trabalhos=TrabalhoRequest(ava),
            entregas=EntregaRequest(ava),
            etiquetas=EtiquetaRequest(ava),
            repository=trabalhos_db,
            materias=materias_db,
            capturas=capturas_db,
        )
        aulas_service = AulaSyncService(
            session=session,
            aulas=AulaRequest(ava),
            atividades=AulaAtividadeRequest(ava),
            materiais=MaterialRequest(ava),
            repository=aulas_db,
            materias=materias_db,
            capturas=capturas_db,
        )
        app = UninterApp(
            materias_service,
            atividades_service,
            trabalhos_service,
            aulas_service,
            ProvaService(AvaProvas(ava), atividades_request),
            agendamentos_service,
            materias_db,
            atividades_db,
            agendamentos_db,
            trabalhos_db,
            aulas_db,
            capturas_db,
            gabaritos_service,
            figures,
            Arquivos(settings.aulas_dir, ArquivoRequest(public_http)),
            MockedMateria(session),
            Config.load(),
            ava,
            TurmaRequest(ava),
            credenciais,
            credenciais_db,
            log,
            ClaudeTerminal(
                choose_launchers(TerminalEnvironment(), sys.platform, shutil.which),
                SystemShell(),
                installed_claude(),
                settings.chat_dir,
            ),
            mcp_url=None if listener is None else listener.url,
            mcp_failure=mcp_failure,
        )
        server = build_server(
            Sources(engine, agendamentos_service, transcricoes_from_cdn(public_http)),
            lambda ctx: app.host,
        )
        async with serving(listener, server):
            await app.run_async()
            app.host.close()
        return app.reset_requested


def keep_library_logs_off_the_terminal() -> None:
    logging.getLogger().addHandler(logging.NullHandler())


async def main() -> None:
    keep_library_logs_off_the_terminal()
    settings = Settings.model_validate({})
    # The file can only go once the engine is disposed: deleting it with a live
    # session leaves SQLite reading an orphaned inode and refusing writes.
    while await run(settings):
        DATABASE_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
