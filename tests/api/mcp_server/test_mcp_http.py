import asyncio
import time
from urllib.parse import urlsplit

import pytest
from mcp import Client
from mcp.server.mcpserver import MCPServer

from api.mcp_server.http import McpListener, port_taken

STOP_DEADLINE_SECONDS = 4.0


def server_with_a_stuck_tool(called: asyncio.Event) -> MCPServer:
    server = MCPServer("uninter")

    async def stuck() -> str:
        called.set()
        await asyncio.Event().wait()
        return "never"

    async def ping() -> str:
        return "pong"

    server.add_tool(stuck)
    server.add_tool(ping)
    return server


def port_of(listener: McpListener) -> int:
    port = urlsplit(listener.url).port
    assert port is not None
    return port


async def call_stuck(url: str) -> None:
    async with Client(url) as client:
        await client.call_tool("stuck", {})


async def test_the_server_answers_on_its_url_and_on_localhost() -> None:
    listener = McpListener.bind("127.0.0.1", 0)
    async with listener.serving(server_with_a_stuck_tool(asyncio.Event())):
        async with Client(listener.url) as client:
            by_ip = await client.call_tool("ping", {})
        localhost = listener.url.replace("127.0.0.1", "localhost")
        async with Client(localhost) as client:
            by_name = await client.call_tool("ping", {})

    assert not by_ip.is_error
    assert not by_name.is_error


def test_a_taken_port_fails_to_bind_and_says_which() -> None:
    first = McpListener.bind("127.0.0.1", 0)
    port = port_of(first)
    try:
        with pytest.raises(OSError) as raised:
            McpListener.bind("127.0.0.1", port)
    finally:
        first.close()

    assert f"127.0.0.1:{port}" in port_taken("127.0.0.1", port, raised.value)


async def test_stopping_does_not_wait_for_a_stuck_call_and_frees_the_port() -> None:
    called = asyncio.Event()
    listener = McpListener.bind("127.0.0.1", 0)
    port = port_of(listener)
    async with listener.serving(server_with_a_stuck_tool(called)):
        caller = asyncio.ensure_future(call_stuck(listener.url))
        await asyncio.wait_for(called.wait(), STOP_DEADLINE_SECONDS)
        started = time.monotonic()
    stopped_in = time.monotonic() - started
    finished, _ = await asyncio.wait({caller}, timeout=STOP_DEADLINE_SECONDS)

    assert stopped_in < STOP_DEADLINE_SECONDS
    assert caller in finished
    McpListener.bind("127.0.0.1", port).close()
