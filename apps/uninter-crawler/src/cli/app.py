from datetime import datetime

from avaliacoes.media import Media
from avaliacoes.repository import AvaliacaoRepository
from avaliacoes.service import AvaliacaoSyncService
from infra.ava import LoginRejected
from materias.entity import Materia
from materias.repository import MateriaRepository
from materias.service import MateriaSyncService

from . import render
from .prompts import BACK, ask_materia, ask_text_choice

VIEW_AVALIACOES = "Ver avaliações de uma matéria"
SYNC_MATERIAS = "Sincronizar matérias"
QUIT = "Sair"
REFRESH = "Atualizar esta matéria"


def sync_materias(service: MateriaSyncService) -> None:
    with render.status("Entrando no AVA..."):
        materias = service.sync()
    render.render_sync_summary(service.aluno, len(materias))


def sync_avaliacoes(service: AvaliacaoSyncService, materia: Materia) -> None:
    with render.status(f"Buscando avaliações de {materia.nome}..."):
        service.sync(materia)


def open_materia(
    avaliacoes_service: AvaliacaoSyncService,
    avaliacoes_db: AvaliacaoRepository,
    materia: Materia,
) -> None:
    while True:
        if materia.avaliacoes_sincronizadas_em is None:
            sync_avaliacoes(avaliacoes_service, materia)
        avaliacoes = avaliacoes_db.list_all(materia)
        render.render_avaliacoes(
            materia, avaliacoes, Media.from_avaliacoes(avaliacoes), datetime.now()
        )
        if ask_text_choice(f"{materia.nome}:", [BACK, REFRESH]) != REFRESH:
            return
        sync_avaliacoes(avaliacoes_service, materia)


def run(
    materias_service: MateriaSyncService,
    avaliacoes_service: AvaliacaoSyncService,
    materias_db: MateriaRepository,
    avaliacoes_db: AvaliacaoRepository,
) -> None:
    try:
        if not materias_db.list_all():
            sync_materias(materias_service)
        while True:
            choice = ask_text_choice(
                "O que você quer fazer?",
                [VIEW_AVALIACOES, SYNC_MATERIAS, QUIT],
            )
            if choice is None or choice == QUIT:
                return
            if choice == SYNC_MATERIAS:
                sync_materias(materias_service)
                continue
            materia = ask_materia(materias_db.list_all())
            if materia is not None:
                open_materia(avaliacoes_service, avaliacoes_db, materia)
    except LoginRejected as rejection:
        render.render_login_rejected(str(rejection))
    except KeyboardInterrupt:
        render.render_goodbye()
