import asyncio

from sqlmodel.ext.asyncio.session import AsyncSession

from api.capturas.entity import AULAS
from api.capturas.repository import CapturaRepository
from api.materias.entity import Materia
from api.materias.repository import MateriaRepository
from crawler.aulas.request import (
    AulaAtividadeRequest,
    AulaRequest,
    FetchResult,
    MaterialRequest,
)

from .entity import Aula, AulaAtividade, Material
from .repository import AulaRepository


class AulaSyncService:
    def __init__(
        self,
        session: AsyncSession,
        aulas: AulaRequest,
        atividades: AulaAtividadeRequest,
        materiais: MaterialRequest,
        repository: AulaRepository,
        materias: MateriaRepository,
        capturas: CapturaRepository,
    ) -> None:
        self._session = session
        self._aulas = aulas
        self._atividades = atividades
        self._materiais = materiais
        self._repository = repository
        self._materias = materias
        self._capturas = capturas

    async def sync(self, materia: Materia) -> list[Aula]:
        result = await self._aulas.fetch(materia)
        atividades, materiais = await self._fetch_details(materia, result.aulas)
        return await asyncio.shield(self._store(materia, result, atividades, materiais))

    async def _fetch_details(
        self, materia: Materia, aulas: list[Aula]
    ) -> tuple[list[AulaAtividade], list[Material]]:
        atividades: list[AulaAtividade] = []
        materiais: list[Material] = []
        for aula in aulas:
            for atividade in await self._atividades.fetch(materia, aula):
                atividades.append(atividade)
                materiais += await self._materiais.fetch(atividade)
        return atividades, materiais

    async def _store(
        self,
        materia: Materia,
        result: FetchResult,
        atividades: list[AulaAtividade],
        materiais: list[Material],
    ) -> list[Aula]:
        await self._repository.replace(materia, result.aulas, atividades, materiais)
        if result.response is not None:
            await self._capturas.replace(result.response.to_captura(AULAS, materia.id))
        await self._materias.mark_aulas_synced(materia)
        await self._session.commit()
        return result.aulas
