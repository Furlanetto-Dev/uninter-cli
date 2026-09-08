import asyncio

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
        # Cancelar no meio da escrita deixa a sessao num estado que nem o rollback
        # recupera; o shield garante que ela termine mesmo se o fetch for abortado.
        return await asyncio.shield(self._gravar(materia, atividades))

    async def _gravar(
        self, materia: Materia, atividades: list[Atividade]
    ) -> list[Atividade]:
        await self._repository.replace(materia, atividades)
        await self._materias.mark_atividades_synced(materia)
        await self._sessao.commit()
        return atividades
