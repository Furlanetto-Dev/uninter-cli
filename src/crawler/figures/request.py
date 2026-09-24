from crawler.session import AvaSession


class FigureRequest:
    def __init__(self, ava: AvaSession) -> None:
        self._ava = ava

    async def fetch(self, url: str) -> bytes | None:
        return await self._ava.get_bytes(url)
