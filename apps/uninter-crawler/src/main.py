from avaliacoes.gateway import AvaliacaoGateway
from avaliacoes.repository import AvaliacaoRepository
from avaliacoes.service import AvaliacaoSyncService
from cli.app import run
from infra.ava import AvaSession, ava_client
from infra.db import db_session
from materias.gateway import MateriaGateway
from materias.repository import MateriaRepository
from materias.service import MateriaSyncService
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
            gateway=MateriaGateway(ava, settings.id_curso),
            repository=materias_db,
        )
        avaliacoes_service = AvaliacaoSyncService(
            sessao=sessao,
            gateway=AvaliacaoGateway(ava),
            repository=avaliacoes_db,
            materias=materias_db,
        )
        run(materias_service, avaliacoes_service, materias_db, avaliacoes_db)


if __name__ == "__main__":
    main()
