"""stdio bridge to the vault server, for clients that only launch local commands.

Claude Desktop reads MCP servers from claude_desktop_config.json and starts each
one as a subprocess speaking stdio; it cannot attach a bearer token to a local
HTTP URL. This bridge runs as that subprocess and forwards tools to the
authenticated SSE endpoint, keeping the scope checks on the server side.
"""
from __future__ import annotations

from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, Tool


def _bridge(remote: ClientSession, *, name: str, instructions: str | None) -> Server:
    bridge = Server(name, instructions=instructions)

    @bridge.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
    async def list_tools() -> list[Tool]:
        return (await remote.list_tools()).tools

    @bridge.call_tool()  # type: ignore[untyped-decorator]
    async def call_tool(name: str, arguments: dict[str, object] | None) -> CallToolResult:
        return await remote.call_tool(name, arguments)

    return bridge


async def run_stdio_proxy(url: str, token: str) -> None:
    async with (
        sse_client(url, headers={"Authorization": f"Bearer {token}"}) as (remote_read, remote_write),
        ClientSession(remote_read, remote_write) as remote,
    ):
        init = await remote.initialize()
        bridge = _bridge(remote, name=init.serverInfo.name, instructions=init.instructions)
        async with stdio_server() as (local_read, local_write):
            await bridge.run(local_read, local_write, bridge.create_initialization_options())


# Older imports.
run_cursor_proxy = run_stdio_proxy
