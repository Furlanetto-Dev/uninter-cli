from sqlmodel.ext.asyncio.session import AsyncSession

from .entity import REMEMBERED_ID, Credencial


class CredencialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self) -> Credencial | None:
        return await self._session.get(Credencial, REMEMBERED_ID)

    async def remember(self, ru: str, password: str, course_id: int) -> None:
        await self._session.merge(
            Credencial(id=REMEMBERED_ID, ru=ru, password=password, course_id=course_id)
        )
        await self._session.commit()

    async def forget(self) -> None:
        stored = await self.find()
        if stored is None:
            return
        await self._session.delete(stored)
        await self._session.commit()
