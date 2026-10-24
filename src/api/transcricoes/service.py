from sqlmodel.ext.asyncio.session import AsyncSession

from api.aulas.entity import Aula, AulaAtividade, Material
from api.aulas.repository import AulaRepository
from crawler.transcricoes.request import TranscricaoRequest

from .entity import Transcricao, has_every_bloco
from .repository import TranscricaoRepository


class TranscricaoService:
    def __init__(
        self,
        session: AsyncSession,
        request: TranscricaoRequest,
        repository: TranscricaoRepository,
        aulas: AulaRepository,
    ) -> None:
        self._session = session
        self._request = request
        self._repository = repository
        self._aulas = aulas

    async def of_aula(self, aula: Aula) -> list[Transcricao]:
        transcricoes: list[Transcricao] = []
        for atividade in await self._aulas.list_atividades(aula):
            for material in await self._aulas.list_materiais(atividade):
                transcricoes += await self._of_material(atividade, material)
        return transcricoes

    async def _of_material(
        self, atividade: AulaAtividade, material: Material
    ) -> list[Transcricao]:
        stored = await self._repository.of_material(material)
        if has_every_bloco(stored):
            return stored
        ordens = {transcricao.ordem for transcricao in stored}
        missing = await self._request.fetch(atividade, material, ordens)
        if missing:
            await self._repository.upsert(missing)
            await self._session.commit()
        return sorted(stored + missing, key=by_ordem)


def by_ordem(transcricao: Transcricao) -> int:
    return transcricao.ordem
