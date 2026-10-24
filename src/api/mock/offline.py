import httpx

from crawler.session import LOGIN_PATH

MOCKED_LOGIN: dict[str, object] = {
    "usuario": {
        "idUsuario": -1,
        "idGrupoEstrutura": -1,
        "nome": "Aluno mockado",
        "time": "0",
    }
}
NO_SESSION_STATUS = 401


class OfflineLogin(httpx.AsyncBaseTransport):
    def __init__(self, inner: httpx.AsyncBaseTransport) -> None:
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith(LOGIN_PATH):
            return httpx.Response(200, json=MOCKED_LOGIN, request=request)
        return await self._inner.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


class NoSession(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(NO_SESSION_STATUS, request=request)
