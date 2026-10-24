import asyncio
import contextlib
import socket
from collections.abc import AsyncGenerator, Generator

import uvicorn
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

MCP_PATH = "/mcp"
LOCALHOST = "localhost"
GRACE_SECONDS = 2
STOP_PATIENCE_SECONDS = 3
PORT_TAKEN = "O MCP não subiu: {host}:{port} já está em uso ({error})."


class QuietServer(uvicorn.Server):
    @contextlib.contextmanager
    def capture_signals(self) -> Generator[None]:
        yield


def port_taken(host: str, port: int, error: OSError) -> str:
    return PORT_TAKEN.format(host=host, port=port, error=error.strerror or error)


class McpListener:
    def __init__(self, bound: socket.socket, host: str, port: int) -> None:
        self._socket = bound
        self._host = host
        self._port = port

    @classmethod
    def bind(cls, host: str, port: int) -> "McpListener":
        bound = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        bound.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            bound.bind((host, port))
            bound.listen()
        except OSError:
            bound.close()
            raise
        return cls(bound, host, bound.getsockname()[1])

    @property
    def url(self) -> str:
        return f"http://{self._host}:{self._port}{MCP_PATH}"

    def _security(self) -> TransportSecuritySettings:
        names = (self._host, LOCALHOST)
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[f"{name}:{self._port}" for name in names],
            allowed_origins=[f"http://{name}:{self._port}" for name in names],
        )

    @contextlib.asynccontextmanager
    async def serving(self, server: MCPServer) -> AsyncGenerator[None]:
        app = server.streamable_http_app(
            streamable_http_path=MCP_PATH,
            transport_security=self._security(),
            host=self._host,
        )
        config = uvicorn.Config(
            app,
            log_config=None,
            access_log=False,
            timeout_graceful_shutdown=GRACE_SECONDS,
        )
        quiet = QuietServer(config)
        task = asyncio.create_task(quiet.serve(sockets=[self._socket]))
        try:
            yield
        finally:
            quiet.should_exit = True
            await stopped(task)
            self.close()

    def close(self) -> None:
        self._socket.close()


async def stopped(task: asyncio.Task[None]) -> None:
    await asyncio.wait({task}, timeout=STOP_PATIENCE_SECONDS)
    if not task.done():
        task.cancel()
        await asyncio.wait({task})
    swallow_failure(task)


def swallow_failure(task: asyncio.Task[None]) -> None:
    if not task.cancelled():
        task.exception()


@contextlib.asynccontextmanager
async def serving(
    listener: McpListener | None, server: MCPServer
) -> AsyncGenerator[None]:
    if listener is None:
        yield
        return
    async with listener.serving(server):
        yield
