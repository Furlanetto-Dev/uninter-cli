from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .entity import Captura


class CapturaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, recurso: str, materia_id: int | None) -> Captura | None:
        statement = select(Captura).where(
            col(Captura.recurso) == recurso,
            col(Captura.materia_id) == materia_id,
        )
        return (await self._session.exec(statement)).first()

    async def replace(self, captura: Captura) -> None:
        stored = await self.find(captura.recurso, captura.materia_id)
        if stored is not None:
            await self._session.delete(stored)
        self._session.add(captura)
