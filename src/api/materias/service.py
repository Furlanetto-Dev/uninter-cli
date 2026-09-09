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
        session: AsyncSession,
        ava: AvaSession,
        request: MateriaRequest,
        repository: MateriaRepository,
        capturas: CapturaRepository,
    ) -> None:
        self._session = session
        self._ava = ava
        self._request = request
        self._repository = repository
        self._capturas = capturas

    @property
    def student(self) -> str | None:
        return self._ava.student

    async def sync(self) -> list[Materia]:
        result = await self._request.fetch()
        await self._repository.save(result.materias)
        await self._capturas.replace(result.response.to_captura(MATERIAS, None))
        await self._session.commit()
        return result.materias
