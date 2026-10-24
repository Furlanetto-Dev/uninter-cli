from collections.abc import Callable
from typing import NamedTuple, cast

import httpx

Payload = Callable[[str, str], dict[str, object] | None]
Figure = Callable[[str], bytes | None]


class Document(NamedTuple):
    body: bytes
    content_type: str


Documents = Callable[[str], Document | None]
MOCK_STATUS = 200
MOCKED = "mocked"
IMAGE_TYPE = "image/png"


class FakeAva(httpx.AsyncBaseTransport):
    def __init__(
        self,
        payload: Payload,
        figure: Figure,
        documents: Documents,
        real: httpx.AsyncBaseTransport,
    ) -> None:
        self._payload = payload
        self._figure = figure
        self._documents = documents
        self._real = real

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        answer = self._payload(str(request.url), request.content.decode())
        if answer is not None:
            return httpx.Response(
                MOCK_STATUS,
                json=cast(object, answer),
                request=request,
                extensions={MOCKED: True},
            )
        image = self._figure(str(request.url))
        if image is not None:
            return httpx.Response(
                MOCK_STATUS,
                content=image,
                headers={"content-type": IMAGE_TYPE},
                request=request,
                extensions={MOCKED: True},
            )
        document = self._documents(str(request.url))
        if document is not None:
            return httpx.Response(
                MOCK_STATUS,
                content=document.body,
                headers={"content-type": document.content_type},
                request=request,
                extensions={MOCKED: True},
            )
        return await self._real.handle_async_request(request)

    async def aclose(self) -> None:
        await self._real.aclose()
