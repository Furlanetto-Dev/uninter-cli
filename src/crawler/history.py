import re
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

import httpx

KEPT = 50
REDACTED = "••••••"
SENHA = re.compile(r"(senha=)[^&]*")
DECODE_ERRORS = "replace"
MOCKED = "mocked"
COOKIE = "cookie"
X_TIME = "x-time"
TOKEN_PLACEHOLDER = "$UNINTER_TIME=$UNINTER_TOKEN"
TIME_PLACEHOLDER = "$UNINTER_TIME"
NOISE = ("host", "content-length", "accept-encoding", "connection")
READABLE_TYPES = ("text/", "application/json", "application/javascript")
CONTENT_TYPE = "content-type"
NOT_READABLE = "<{kind}, {size} bytes>"


@dataclass
class Request:
    method: str
    url: str
    sent: str
    at: datetime
    status: int | None = None
    received: str = ""
    elapsed: float | None = None
    error: str | None = None
    mocked: bool = False
    headers: dict[str, str] = field(default_factory=dict[str, str])

    def as_curl(self) -> str:
        lines = [f"curl --request {self.method} \\", f"  --url '{self.url}' \\"]
        lines += [
            f"  --header '{name}: {value}' \\" for name, value in self.headers.items()
        ]
        if self.sent:
            lines.append(f"  --data-raw '{self.sent}' \\")
        return "\n".join(lines).removesuffix(" \\")

    @property
    def answered(self) -> bool:
        return self.status is not None or self.error is not None


def body_of(response: httpx.Response) -> str:
    kind = response.headers.get(CONTENT_TYPE, "")
    if not kind or kind.startswith(READABLE_TYPES):
        return response.text
    return NOT_READABLE.format(kind=kind, size=len(response.content))


def redact(body: str) -> str:
    return SENHA.sub(rf"\g<1>{REDACTED}", body)


def safe_headers(headers: Mapping[str, str]) -> dict[str, str]:
    kept: dict[str, str] = {}
    for name, value in headers.items():
        lowered = name.lower()
        if lowered in NOISE:
            continue
        if lowered == COOKIE:
            value = TOKEN_PLACEHOLDER
        elif lowered == X_TIME:
            value = TIME_PLACEHOLDER
        kept[lowered] = value
    return kept


class RequestLog:
    def __init__(self, kept: int = KEPT) -> None:
        self._entries: deque[Request] = deque(maxlen=kept)
        self._listeners: list[Callable[[], None]] = []

    @property
    def entries(self) -> list[Request]:
        return list(reversed(self._entries))

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def unsubscribe(self, listener: Callable[[], None]) -> None:
        if listener in self._listeners:
            self._listeners.remove(listener)

    def opened(
        self, method: str, url: str, sent: str, headers: Mapping[str, str] = {}
    ) -> Request:
        entry = Request(
            method=method,
            url=url,
            sent=redact(sent),
            at=datetime.now(),
            headers=safe_headers(headers),
        )
        self._entries.append(entry)
        self._announce()
        return entry

    def closed(
        self, entry: Request, status: int, received: str, mocked: bool = False
    ) -> None:
        entry.status = status
        entry.received = received
        entry.mocked = mocked
        entry.elapsed = (datetime.now() - entry.at).total_seconds()
        self._announce()

    def failed(self, error: str) -> None:
        for entry in reversed(self._entries):
            if not entry.answered:
                entry.error = error
                entry.elapsed = (datetime.now() - entry.at).total_seconds()
                break
        self._announce()

    def _announce(self) -> None:
        for listener in list(self._listeners):
            listener()


def hooks(log: RequestLog) -> dict[str, list[Callable[..., object]]]:
    pending: dict[int, Request] = {}

    async def on_request(request: httpx.Request) -> None:
        sent = request.content.decode(errors=DECODE_ERRORS)
        pending[id(request)] = log.opened(
            request.method, str(request.url), sent, request.headers
        )

    async def on_response(response: httpx.Response) -> None:
        entry = pending.pop(id(response.request), None)
        if entry is None:
            return
        await response.aread()
        mocked = bool(response.extensions.get(MOCKED))
        log.closed(entry, response.status_code, body_of(response), mocked)

    return {"request": [on_request], "response": [on_response]}
