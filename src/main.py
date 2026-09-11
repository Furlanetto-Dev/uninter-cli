import asyncio

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.repository import CapturaRepository
from api.db import DATABASE_PATH, db_session
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from cli.app import UninterApp
from crawler.atividades.prova_mock import CAPTURE, MockProvaSource
from crawler.atividades.request import AtividadeRequest
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession, ava_client
from crawler.trabalhos.request import EntregaRequest, EtiquetaRequest, TrabalhoRequest
from settings import Settings


async def run(settings: Settings) -> bool:
    async with ava_client() as http, db_session() as session:
        ava = AvaSession(http, settings.ru, settings.password)
        materias_db = MateriaRepository(session)
        atividades_db = AtividadeRepository(session)
        trabalhos_db = TrabalhoRepository(session)
        capturas_db = CapturaRepository(session)
        materias_service = MateriaSyncService(
            session=session,
            ava=ava,
            request=MateriaRequest(ava, settings.course_id),
            repository=materias_db,
            capturas=capturas_db,
        )
        atividades_service = AtividadeSyncService(
            session=session,
            request=AtividadeRequest(ava),
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
        app = UninterApp(
            materias_service,
            atividades_service,
            trabalhos_service,
            # 0015: the mocked prova, until the start call is written.
            MockProvaSource(CAPTURE),
            materias_db,
            atividades_db,
            trabalhos_db,
            capturas_db,
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
