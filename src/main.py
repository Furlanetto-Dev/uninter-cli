import asyncio

import httpx

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.aulas.arquivos import Arquivos
from api.aulas.repository import AulaRepository
from api.aulas.service import AulaSyncService
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.db import DATABASE_PATH, db_session
from api.figures.repository import FigureRepository
from api.figures.service import FigureService
from api.gabaritos.repository import GabaritoRepository
from api.gabaritos.service import GabaritoService
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.mock import fixture
from api.mock.seed import MockedMateria
from api.provas.service import ProvaService
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from cli.app import UninterApp
from cli.figures import Figures, painter
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
from crawler.figures.request import FigureRequest
from crawler.history import RequestLog
from crawler.materias.request import MateriaRequest
from crawler.mock import FakeAva
from crawler.session import AvaSession, ava_client
from crawler.trabalhos.request import EntregaRequest, EtiquetaRequest, TrabalhoRequest
from settings import Settings


def from_env(settings: Settings) -> Credenciais:
    if settings.ru is None or settings.password is None or settings.course_id is None:
        return Credenciais()
    return Credenciais(settings.ru, settings.password, settings.course_id)


async def stored(
    credenciais: Credenciais, credenciais_db: CredencialRepository
) -> Credenciais:
    if credenciais.filled:
        return credenciais
    remembered = await credenciais_db.find()
    if remembered is not None:
        credenciais.fill(remembered.ru, remembered.password, remembered.course_id)
    return credenciais


async def run(settings: Settings) -> bool:
    log = RequestLog()
    transport = FakeAva(
        fixture.MockedAva().payload, fixture.figure, httpx.AsyncHTTPTransport()
    )
    async with ava_client(transport, log) as http, db_session() as session:
        credenciais_db = CredencialRepository(session)
        credenciais = await stored(from_env(settings), credenciais_db)
        ava = AvaSession(http, credenciais, log)
        materias_db = MateriaRepository(session)
        atividades_db = AtividadeRepository(session)
        trabalhos_db = TrabalhoRepository(session)
        aulas_db = AulaRepository(session)
        capturas_db = CapturaRepository(session)
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
            materias_db,
            atividades_db,
            trabalhos_db,
            aulas_db,
            capturas_db,
            gabaritos_service,
            figures,
            Arquivos(settings.aulas_dir, ArquivoRequest(http)),
            MockedMateria(session),
            Config.load(),
            ava,
            credenciais,
            credenciais_db,
            log,
        )
        await app.run_async()
        return app.reset_requested


async def main() -> None:
    settings = Settings.model_validate({})
    # The file can only go once the engine is disposed: deleting it with a live
    # session leaves SQLite reading an orphaned inode and refusing writes.
    while await run(settings):
        DATABASE_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
