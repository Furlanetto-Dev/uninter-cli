import asyncio

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.capturas.repository import CapturaRepository
from api.db import DATABASE_PATH, db_session
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from cli.app import UninterApp
from crawler.atividades.request import AtividadeRequest
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession, ava_client
from settings import Settings


async def rodar(settings: Settings) -> bool:
    async with ava_client() as http, db_session() as sessao:
        ava = AvaSession(http, settings.ru, settings.senha)
        materias_db = MateriaRepository(sessao)
        atividades_db = AtividadeRepository(sessao)
        capturas_db = CapturaRepository(sessao)
        materias_service = MateriaSyncService(
            sessao=sessao,
            ava=ava,
            request=MateriaRequest(ava, settings.id_curso),
            repository=materias_db,
            capturas=capturas_db,
        )
        atividades_service = AtividadeSyncService(
            sessao=sessao,
            request=AtividadeRequest(ava),
            repository=atividades_db,
            materias=materias_db,
            capturas=capturas_db,
        )
        app = UninterApp(
            materias_service,
            atividades_service,
            materias_db,
            atividades_db,
            capturas_db,
        )
        await app.run_async()
        return app.resetar


async def main() -> None:
    settings = Settings.model_validate({})
    # O arquivo só pode sumir depois que o engine foi descartado: apagá-lo com a
    # sessão viva deixa o SQLite lendo de um inode órfão e recusando escrita.
    while await rodar(settings):
        DATABASE_PATH.unlink(missing_ok=True)


if __name__ == "__main__":
    asyncio.run(main())
