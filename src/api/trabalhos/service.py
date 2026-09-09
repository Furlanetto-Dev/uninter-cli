import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from api.capturas.entity import TRABALHOS
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.trabalhos.request import (
    EntregaRequest,
    EtiquetaRequest,
    FetchResult,
    TrabalhoRequest,
)

from .entity import Trabalho, TrabalhoEntrega, TrabalhoEtiqueta
from .repository import TrabalhoRepository


class TrabalhoSyncService:
    def __init__(
        self,
        session: AsyncSession,
        trabalhos: TrabalhoRequest,
        entregas: EntregaRequest,
        etiquetas: EtiquetaRequest,
        repository: TrabalhoRepository,
        materias: MateriaRepository,
        capturas: CapturaRepository,
    ) -> None:
        self._session = session
        self._trabalhos = trabalhos
        self._entregas = entregas
        self._etiquetas = etiquetas
        self._repository = repository
        self._materias = materias
        self._capturas = capturas

    async def sync(self, materia: Materia) -> list[Trabalho]:
        result = await self._trabalhos.fetch(materia)
        entregas, etiquetas = await self._fetch_details(result.trabalhos)
        # Cancelling mid-write leaves the session in a state not even rollback
        # recovers; the shield lets it finish even if the fetch gets aborted.
        return await asyncio.shield(self._store(materia, result, entregas, etiquetas))

    async def _fetch_details(
        self, trabalhos: list[Trabalho]
    ) -> tuple[list[TrabalhoEntrega], list[TrabalhoEtiqueta]]:
        entregas: list[TrabalhoEntrega] = []
        etiquetas: list[TrabalhoEtiqueta] = []
        for trabalho in trabalhos:
            for entrega in await self._entregas.fetch(trabalho):
                entregas.append(entrega)
                if entrega.correcao_id is not None:
                    etiquetas += await self._etiquetas.fetch(entrega.correcao_id)
        return entregas, etiquetas

    async def _store(
        self,
        materia: Materia,
        result: FetchResult,
        entregas: list[TrabalhoEntrega],
        etiquetas: list[TrabalhoEtiqueta],
    ) -> list[Trabalho]:
        await self._repository.replace(materia, result.trabalhos, entregas, etiquetas)
        await self._capturas.replace(result.response.to_captura(TRABALHOS, materia.id))
        await self._materias.mark_trabalhos_synced(materia)
        await self._session.commit()
        return result.trabalhos
