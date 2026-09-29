"""Legacy stdio bridge for Cursor installations without remote URL support."""
from __future__ import annotations

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool


def _bridge(remote: ClientSession) -> Server:
    bridge = Server("obsidian-context-proxy")

    @bridge.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def list_tools() -> list[Tool]:
        return (await remote.list_tools()).tools

    @bridge.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, object] | None) -> CallToolResult:
        return await remote.call_tool(name, arguments)

    return bridge


async def run_cursor_proxy(url: str, token: str) -> None:
    async with (
        sse_client(url, headers={"Authorization": f"Bearer {token}"}) as (remote_read, remote_write),
        ClientSession(remote_read, remote_write) as remote,
    ):
        await remote.initialize()
        bridge = _bridge(remote)
        async with stdio_server() as (local_read, local_write):
            await bridge.run(local_read, local_write, bridge.create_initialization_options())
