from __future__ import annotations

import asyncio
import json
import socket
import threading
from pathlib import Path

import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.sse import sse_client

from obsidian_context_mcp.core.vault_context import get_vault_context
from obsidian_context_mcp.shared.types import AccessScope
from obsidian_context_mcp.vault_server.http_app import create_http_app


@pytest.mark.asyncio
async def test_sse_session_is_bound_to_scope_token(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    ctx = get_vault_context(str(vault), data_dir=tmp_path / "data")
    ctx.scope_store.upsert(AccessScope(id="first", name="First", token="first-secret"))
    ctx.scope_store.upsert(AccessScope(id="second", name="Second", token="second-secret"))
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(create_http_app(ctx, admin_token="admin-secret"), host="127.0.0.1", port=port, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        async with httpx.AsyncClient() as http:
            for _ in range(100):
                try:
                    if (await http.get(f"http://127.0.0.1:{port}/health")).status_code == 200:
                        break
                except httpx.ConnectError:
                    pass
                await asyncio.sleep(.05)
            else:
                pytest.fail("test server did not start")
            session_ids: list[str] = []
            async with (
                sse_client(f"http://127.0.0.1:{port}/sse", headers={"Authorization": "Bearer first-secret"}, on_session_created=session_ids.append) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                tools = await session.list_tools()
                assert any(tool.name == "scope_get_info" for tool in tools.tools)
                info = await session.call_tool("scope_get_info", {})
                assert not info.isError
                assert json.loads(info.content[0].text)["scopeId"] == "first"
                assert session_ids
                changed = await http.post(f"http://127.0.0.1:{port}/messages/?session_id={session_ids[0]}", headers={"Authorization": "Bearer second-secret"}, json={"jsonrpc": "2.0", "method": "ping"})
                assert changed.status_code == 403
                ctx.scope_store.regenerate_token("first")
                revoked = await http.post(f"http://127.0.0.1:{port}/messages/?session_id={session_ids[0]}", headers={"Authorization": "Bearer first-secret"}, json={"jsonrpc": "2.0", "method": "ping"})
                assert revoked.status_code == 401
    finally:
        server.should_exit = True
        thread.join(timeout=10)
