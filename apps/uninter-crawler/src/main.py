import asyncio

from api.atividades.repository import AtividadeRepository
from api.atividades.service import AtividadeSyncService
from api.db import db_session
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from cli.app import UninterApp
from crawler.atividades.request import AtividadeRequest
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession, ava_client
from settings import Settings


async def main() -> None:
    settings = Settings.model_validate({})
    async with ava_client() as http, db_session() as sessao:
        ava = AvaSession(http, settings.ru, settings.senha)
        materias_db = MateriaRepository(sessao)
        atividades_db = AtividadeRepository(sessao)
        materias_service = MateriaSyncService(
            sessao=sessao,
            ava=ava,
            request=MateriaRequest(ava, settings.id_curso),
            repository=materias_db,
        )
        atividades_service = AtividadeSyncService(
            sessao=sessao,
            request=AtividadeRequest(ava),
            repository=atividades_db,
            materias=materias_db,
        )
        await UninterApp(
            materias_service, atividades_service, materias_db, atividades_db
        ).run_async()


if __name__ == "__main__":
    asyncio.run(main())
