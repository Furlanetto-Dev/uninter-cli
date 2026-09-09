from sqlmodel.ext.asyncio.session import AsyncSession

from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.trabalhos.request import EntregaRequest, EtiquetaRequest, TrabalhoRequest

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
    ) -> None:
        self._session = session
        self._trabalhos = trabalhos
        self._entregas = entregas
        self._etiquetas = etiquetas
        self._repository = repository
        self._materias = materias

    async def sync(self, materia: Materia) -> list[Trabalho]:
        trabalhos = await self._trabalhos.fetch(materia)
        entregas: list[TrabalhoEntrega] = []
        etiquetas: list[TrabalhoEtiqueta] = []
        for trabalho in trabalhos:
            for entrega in await self._entregas.fetch(trabalho):
                entregas.append(entrega)
                if entrega.correcao_id is not None:
                    etiquetas += await self._etiquetas.fetch(entrega.correcao_id)
        await self._repository.replace(materia, trabalhos, entregas, etiquetas)
        await self._materias.mark_trabalhos_synced(materia)
        await self._session.commit()
        return trabalhos
