from datetime import datetime

from sqlmodel import col, select
from sqlmodel.ext.asyncio.session import AsyncSession

from .entity import Figure


class FigureRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find(self, url: str) -> Figure | None:
        statement = select(Figure).where(col(Figure.url) == url)
        return (await self._session.exec(statement)).first()

    async def add(self, figure: Figure) -> None:
        self._session.add(figure)

    async def forget(self, figure: Figure) -> None:
        await self._session.delete(figure)

    async def forget_before(self, moment: datetime) -> int:
        statement = select(Figure).where(col(Figure.fetched_at) < moment)
        stale = list((await self._session.exec(statement)).all())
        for figure in stale:
            await self._session.delete(figure)
        return len(stale)
