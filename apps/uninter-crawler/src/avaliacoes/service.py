from sqlmodel import Session

from materias.entity import Materia
from materias.repository import MateriaRepository

from .entity import Avaliacao
from .gateway import AvaliacaoGateway
from .repository import AvaliacaoRepository


class AvaliacaoSyncService:
    def __init__(
        self,
        sessao: Session,
        gateway: AvaliacaoGateway,
        repository: AvaliacaoRepository,
        materias: MateriaRepository,
    ) -> None:
        self._sessao = sessao
        self._gateway = gateway
        self._repository = repository
        self._materias = materias

    def sync(self, materia: Materia) -> list[Avaliacao]:
        avaliacoes = self._gateway.fetch(materia)
        self._repository.replace(materia, avaliacoes)
        self._materias.mark_synced(materia)
        self._sessao.commit()
        return avaliacoes
