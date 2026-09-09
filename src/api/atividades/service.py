import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from api.capturas.entity import ATIVIDADES
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.atividades.request import AtividadeRequest, FetchResult

from .entity import Atividade
from .repository import AtividadeRepository


class AtividadeSyncService:
    def __init__(
        self,
        session: AsyncSession,
        request: AtividadeRequest,
        repository: AtividadeRepository,
        materias: MateriaRepository,
        capturas: CapturaRepository,
    ) -> None:
        self._session = session
        self._request = request
        self._repository = repository
        self._materias = materias
        self._capturas = capturas

    async def sync(self, materia: Materia) -> list[Atividade]:
        result = await self._request.fetch(materia)
        # Cancelling mid-write leaves the session in a state not even rollback
        # recovers; the shield lets it finish even if the fetch gets aborted.
        return await asyncio.shield(self._store(materia, result))

    async def _store(self, materia: Materia, result: FetchResult) -> list[Atividade]:
        await self._repository.replace(materia, result.atividades)
        await self._capturas.replace(result.response.to_captura(ATIVIDADES, materia.id))
        await self._materias.mark_atividades_synced(materia)
        await self._session.commit()
        return result.atividades
