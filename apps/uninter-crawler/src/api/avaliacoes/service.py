from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.avaliacoes.request import AvaliacaoRequest

from .entity import Avaliacao
from .repository import AvaliacaoRepository


class AvaliacaoSyncService:
    def __init__(
        self,
        sessao: AsyncSession,
        request: AvaliacaoRequest,
        repository: AvaliacaoRepository,
        materias: MateriaRepository,
    ) -> None:
        self._sessao = sessao
        self._request = request
        self._repository = repository
        self._materias = materias

    async def sync(self, materia: Materia) -> list[Avaliacao]:
        avaliacoes = await self._request.fetch(materia)
        await self._repository.replace(materia, avaliacoes)
        await self._materias.mark_synced(materia)
        await self._sessao.commit()
        return avaliacoes
