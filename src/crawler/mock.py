from collections.abc import Callable
from typing import cast

import httpx

Payload = Callable[[str], dict[str, object] | None]
MOCK_STATUS = 200
MOCKED = "mocked"


class FakeAva(httpx.AsyncBaseTransport):
    def __init__(self, payload: Payload, real: httpx.AsyncBaseTransport) -> None:
        self._payload = payload
        self._real = real

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        answer = self._payload(str(request.url))
        if answer is None:
            return await self._real.handle_async_request(request)
        return httpx.Response(
            MOCK_STATUS,
            json=cast(object, answer),
            request=request,
            extensions={MOCKED: True},
        )

    async def aclose(self) -> None:
        await self._real.aclose()
