from sqlmodel.ext.asyncio.session import AsyncSession

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
    ) -> None:
        self._sessao = sessao
        self._ava = ava
        self._request = request
        self._repository = repository

    @property
    def aluno(self) -> str | None:
        return self._ava.aluno

    async def sync(self) -> list[Materia]:
        materias = await self._request.fetch()
        await self._repository.save(materias)
        await self._sessao.commit()
        return materias
