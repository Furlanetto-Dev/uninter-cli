from sqlmodel.ext.asyncio.session import AsyncSession

from api.capturas.entity import MATERIAS
from api.capturas.repository import CapturaRepository
from crawler.materias.request import MateriaRequest
from crawler.session import AvaSession

from .entity import Materia
from .repository import MateriaRepository


class MateriaSyncService:
    def __init__(
        self,
        sessao: AsyncSession,
        ava: AvaSession,
        request: MateriaRequest,
        repository: MateriaRepository,
        capturas: CapturaRepository,
    ) -> None:
        self._sessao = sessao
        self._ava = ava
        self._request = request
        self._repository = repository
        self._capturas = capturas

    @property
    def aluno(self) -> str | None:
        return self._ava.aluno

    async def sync(self) -> list[Materia]:
        result = await self._request.fetch()
        await self._repository.save(result.materias)
        await self._capturas.replace(result.response.to_captura(MATERIAS, None))
        await self._sessao.commit()
        return result.materias
