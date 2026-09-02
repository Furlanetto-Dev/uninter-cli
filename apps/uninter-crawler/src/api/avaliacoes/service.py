from sqlmodel import Session

from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.avaliacoes.request import AvaliacaoRequest

from .entity import Avaliacao
from .repository import AvaliacaoRepository


class AvaliacaoSyncService:
    def __init__(
        self,
        sessao: Session,
        request: AvaliacaoRequest,
        repository: AvaliacaoRepository,
        materias: MateriaRepository,
    ) -> None:
        self._sessao = sessao
        self._request = request
        self._repository = repository
        self._materias = materias

    def sync(self, materia: Materia) -> list[Avaliacao]:
        avaliacoes = self._request.fetch(materia)
        self._repository.replace(materia, avaliacoes)
        self._materias.mark_synced(materia)
        self._sessao.commit()
        return avaliacoes
