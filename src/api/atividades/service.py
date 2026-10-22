import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from api.agendamentos.entity import Agendamento
from api.agendamentos.repository import AgendamentoRepository
from api.agendamentos.service import AgendamentoService
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
        agendamentos: AgendamentoService,
        agendamentos_db: AgendamentoRepository,
    ) -> None:
        self._session = session
        self._request = request
        self._repository = repository
        self._materias = materias
        self._capturas = capturas
        self._agendamentos = agendamentos
        self._agendamentos_db = agendamentos_db

    async def sync(self, materia: Materia) -> list[Atividade]:
        result = await self._request.fetch(materia)
        agendamentos = await self._agendamentos.fetch_if_schedulable(
            materia, result.atividades
        )
        # Cancelling mid-write leaves the session in a state not even rollback
        # recovers; the shield lets it finish even if the fetch gets aborted.
        return await asyncio.shield(self._store(materia, result, agendamentos))

    async def _store(
        self,
        materia: Materia,
        result: FetchResult,
        agendamentos: list[Agendamento] | None,
    ) -> list[Atividade]:
        await self._repository.replace(materia, result.atividades)
        if agendamentos is not None:
            await self._agendamentos_db.replace(materia, agendamentos)
        await self._capturas.replace(result.response.to_captura(ATIVIDADES, materia.id))
        await self._materias.mark_atividades_synced(materia)
        await self._session.commit()
        return result.atividades
