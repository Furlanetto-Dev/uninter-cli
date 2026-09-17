from datetime import datetime
from typing import NamedTuple

import httpx

from api.capturas.entity import Captura

from .credenciais import Credenciais
from .dto import LoginDTO
from .history import RequestLog, hooks

BASE_URL = "https://univirtus.uninter.com/ava"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
)
FORM_CONTENT_TYPE = "application/x-www-form-urlencoded; charset=UTF-8"
NO_RECORDS_STATUS = 404
TIMEOUT_SECONDS = 30


class LoginRejected(Exception):
    pass


class AvaUnreachable(Exception):
    pass


class AvaResponse(NamedTuple):
    url: str
    status: int
    text: str
    json: object | None

    def to_captura(self, recurso: str, materia_id: int | None) -> Captura:
        return Captura(
            recurso=recurso,
            materia_id=materia_id,
            url=self.url,
            status=self.status,
            corpo=self.text,
            recebida_em=datetime.now(),
        )


def ava_client(
    transport: httpx.AsyncBaseTransport | None = None,
    log: RequestLog | None = None,
) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=transport,
        event_hooks=hooks(log) if log is not None else None,
        base_url=BASE_URL,
        timeout=TIMEOUT_SECONDS,
        headers={
            "accept": "application/json, text/javascript, */*; q=0.01",
            "referer": f"{BASE_URL}/web/",
            "user-agent": USER_AGENT,
            "x-requested-with": "XMLHttpRequest",
        },
    )


class AvaSession:
    def __init__(
        self,
        http: httpx.AsyncClient,
        credenciais: Credenciais,
        log: RequestLog | None = None,
    ) -> None:
        self._http = http
        self._credenciais = credenciais
        self._log = log
        self._stamp: str | None = None
        self._student: str | None = None

    @property
    def student(self) -> str | None:
        return self._student

    def forget(self) -> None:
        self._stamp = None
        self._student = None
        self._http.cookies.clear()

    async def get(self, url: str) -> AvaResponse:
        try:
            response = await self._http.get(url, headers=await self._session_headers())
        except httpx.TransportError as error:
            self._note(error)
            raise
        if response.status_code == NO_RECORDS_STATUS:
            return AvaResponse(
                str(response.url), response.status_code, response.text, None
            )
        response.raise_for_status()
        return AvaResponse(
            str(response.url), response.status_code, response.text, response.json()
        )

    async def put(self, url: str, data: dict[str, str]) -> AvaResponse:
        headers = await self._session_headers()
        headers["content-type"] = FORM_CONTENT_TYPE
        try:
            response = await self._http.put(url, data=data, headers=headers)
        except httpx.TransportError as error:
            self._note(error)
            raise
        response.raise_for_status()
        return AvaResponse(
            str(response.url), response.status_code, response.text, response.json()
        )

    def _note(self, error: httpx.TransportError) -> None:
        if self._log is not None:
            self._log.failed(f"{type(error).__name__}: {error}")

    async def _session_headers(self) -> dict[str, str]:
        stamp = self._stamp
        if stamp is None:
            stamp = await self.log_in()
        # The AVA names its session cookie with a timestamp and expects x-time to echo it.
        return {"x-time": stamp}

    async def log_in(self) -> str:
        try:
            response = await self._http.post(
                "/autenticacao/autenticar/false/Post",
                data={
                    "login": self._credenciais.ru,
                    "senha": self._credenciais.password,
                    "recaptcha": "",
                },
                headers={"content-type": FORM_CONTENT_TYPE},
            )
        except httpx.TransportError as error:
            self._note(error)
            raise AvaUnreachable(str(error)) from error
        response.raise_for_status()
        dto = LoginDTO.model_validate(response.json())
        if dto.usuario is None:
            raise LoginRejected(dto.mensagem or "RU ou senha inválidos")
        self._student = dto.usuario.nome
        self._stamp = dto.usuario.time
        return dto.usuario.time
