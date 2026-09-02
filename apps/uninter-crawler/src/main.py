from api.avaliacoes.repository import AvaliacaoRepository
from api.avaliacoes.service import AvaliacaoSyncService
from api.db import db_session
from api.materias.repository import MateriaRepository
from api.materias.service import MateriaSyncService
from cli.app import run
from crawler.avaliacoes.request import AvaliacaoRequest
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession, ava_client
from settings import Settings


def main() -> None:
    settings = Settings.model_validate({})
    with ava_client() as http, db_session() as sessao:
        ava = AvaSession(http, settings.ru, settings.senha)
        materias_db = MateriaRepository(sessao)
        avaliacoes_db = AvaliacaoRepository(sessao)
        materias_service = MateriaSyncService(
            sessao=sessao,
            ava=ava,
            request=MateriaRequest(ava, settings.id_curso),
            repository=materias_db,
        )
        avaliacoes_service = AvaliacaoSyncService(
            sessao=sessao,
            request=AvaliacaoRequest(ava),
            repository=avaliacoes_db,
            materias=materias_db,
        )
        run(materias_service, avaliacoes_service, materias_db, avaliacoes_db)


if __name__ == "__main__":
    main()
