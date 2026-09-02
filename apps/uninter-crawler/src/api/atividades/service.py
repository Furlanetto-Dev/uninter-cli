from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.atividades.request import AtividadeRequest

from .entity import Atividade
from .repository import AtividadeRepository


class AtividadeSyncService:
    def __init__(
        self,
        sessao: AsyncSession,
        request: AtividadeRequest,
        repository: AtividadeRepository,
        materias: MateriaRepository,
    ) -> None:
        self._sessao = sessao
        self._request = request
        self._repository = repository
        self._materias = materias

    async def sync(self, materia: Materia) -> list[Atividade]:
        atividades = await self._request.fetch(materia)
        await self._repository.replace(materia, atividades)
        await self._materias.mark_synced(materia)
        await self._sessao.commit()
        return atividades
