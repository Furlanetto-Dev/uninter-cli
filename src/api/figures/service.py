import asyncio
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Protocol

import httpx
from sqlmodel.ext.asyncio.session import AsyncSession

from crawler.figures.request import FigureRequest
from crawler.session import AvaUnreachable

from .entity import Figure
from .repository import FigureRepository

KEPT_FOR = timedelta(days=7)
AT_A_TIME = 4


class FigureSource(Protocol):
    async def stored(self, url: str) -> bytes | None: ...

    async def fetch_all(self, urls: Sequence[str]) -> dict[str, bytes]: ...


class FigureService:
    def __init__(
        self,
        session: AsyncSession,
        request: FigureRequest,
        repository: FigureRepository,
        kept_for: timedelta = KEPT_FOR,
    ) -> None:
        self._session = session
        self._request = request
        self._repository = repository
        self._kept_for = kept_for
        self._gate = asyncio.Semaphore(AT_A_TIME)

    async def stored(self, url: str) -> bytes | None:
        found = await self._repository.find(url)
        if found is None:
            return None
        if found.fetched_at >= self._staleness_line():
            return found.data
        await self._repository.forget(found)
        await self._session.commit()
        return None

    async def fetch_all(self, urls: Sequence[str]) -> dict[str, bytes]:
        answers = await asyncio.gather(*(self._fetch(url) for url in urls))
        arrived = {url: data for url, data in zip(urls, answers) if data is not None}
        await self._keep(arrived)
        return arrived

    async def forget_stale(self) -> int:
        forgotten = await self._repository.forget_before(self._staleness_line())
        if forgotten:
            await self._session.commit()
        return forgotten

    def _staleness_line(self) -> datetime:
        return datetime.now() - self._kept_for

    async def _fetch(self, url: str) -> bytes | None:
        async with self._gate:
            try:
                return await self._request.fetch(url)
            except (AvaUnreachable, httpx.HTTPError):
                return None

    async def _keep(self, arrived: dict[str, bytes]) -> None:
        if not arrived:
            return
        moment = datetime.now()
        for url, data in arrived.items():
            await self._repository.add(Figure(url=url, data=data, fetched_at=moment))
        await self._session.commit()
