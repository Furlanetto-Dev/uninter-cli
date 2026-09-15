import asyncio

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.repository import CapturaRepository
from api.credenciais.repository import CredencialRepository
from api.db import DATABASE_PATH, db_session
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from api.mock.provas import MockedProvas
from api.mock.seed import MockedMateria
from api.trabalhos.repository import TrabalhoRepository
from api.trabalhos.service import TrabalhoSyncService
from cli.app import UninterApp
from config import Config
from crawler.atividades.request import AtividadeRequest
from crawler.materias.request import MateriaRequest
from crawler.credenciais import Credenciais
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
    async with ava_client() as http, db_session() as session:
        credenciais_db = CredencialRepository(session)
        credenciais = await stored(from_env(settings), credenciais_db)
        ava = AvaSession(http, credenciais)
        materias_db = MateriaRepository(session)
        atividades_db = AtividadeRepository(session)
        trabalhos_db = TrabalhoRepository(session)
        capturas_db = CapturaRepository(session)
        materias_service = MateriaSyncService(
            session=session,
            ava=ava,
            request=MateriaRequest(ava, credenciais),
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
            MockedProvas(),
            materias_db,
            atividades_db,
            trabalhos_db,
            capturas_db,
            MockedMateria(session),
            Config.load(),
            ava,
            credenciais,
            credenciais_db,
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
