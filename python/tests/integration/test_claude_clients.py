"""Claude Desktop path: stdio proxy → authenticated vault-server, end to end."""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path

import httpx
import pytest
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from starlette.testclient import TestClient

from obsidian_context_mcp.core.vault_context import get_vault_context
from obsidian_context_mcp.shared.types import AccessScope
from obsidian_context_mcp.vault_server.http_app import create_http_app


def _start_server(ctx, port: int) -> uvicorn.Server:  # type: ignore[no-untyped-def]
    server = uvicorn.Server(
        uvicorn.Config(create_http_app(ctx, admin_token="admin-secret"), host="127.0.0.1", port=port, log_level="error")
    )
    threading.Thread(target=server.run, daemon=True).start()
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health").status_code == 200:
                return server
        except httpx.ConnectError:
            time.sleep(0.05)
    raise RuntimeError("server did not start")


@pytest.fixture
def vault_ctx(tmp_path: Path):  # type: ignore[no-untyped-def]
    vault = tmp_path / "vault"
    (vault / "Allowed").mkdir(parents=True)
    (vault / "Allowed" / "Note.md").write_text("# Note\nhello from the vault\n", encoding="utf-8")
    ctx = get_vault_context(str(vault), data_dir=tmp_path / "data")
    ctx.scope_store.upsert(AccessScope(id="s", name="Notes", include=["Allowed/**"], token="scope-secret"))
    return ctx


def test_claude_config_endpoint(vault_ctx) -> None:  # type: ignore[no-untyped-def]
    (vault_ctx.data_dir / "runtime.json").write_text('{"port": 12345}', encoding="utf-8")
    with TestClient(create_http_app(vault_ctx, admin_token="admin-secret")) as client:
        assert client.get("/api/v1/scopes/s/claude-config").status_code == 401
        headers = {"Authorization": "Bearer admin-secret"}
        body = client.get("/api/v1/scopes/s/claude-config", headers=headers).json()
        assert "http://127.0.0.1:12345/mcp" in body["claudeCode"]["command"]
        assert "scope-secret" not in json.dumps(body["claudeCode"]["projectConfig"])
        entry = body["claudeDesktop"]["config"]["mcpServers"]["obsidian-context"]
        assert entry["args"][-3:] == ["stdio-proxy", "--data-dir", str(vault_ctx.data_dir)]
        assert entry["env"]["OBSIDIAN_CONTEXT_SCOPE_TOKEN"] == "scope-secret"
        assert body["claudeDesktop"]["configPath"].endswith("claude_desktop_config.json")
        assert client.get("/api/v1/scopes/missing/claude-config", headers=headers).status_code == 404


def test_install_endpoint_writes_desktop_config(vault_ctx, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "Claude" / "claude_desktop_config.json"
    monkeypatch.setattr(
        "obsidian_context_mcp.vault_server.admin_api.claude_desktop_config_path", lambda: target
    )
    with TestClient(create_http_app(vault_ctx, admin_token="admin-secret")) as client:
        headers = {"Authorization": "Bearer admin-secret"}
        assert client.post("/api/v1/scopes/s/claude-desktop/install").status_code == 401
        result = client.post("/api/v1/scopes/s/claude-desktop/install", headers=headers).json()
        assert result == {"configPath": str(target), "changed": True}
        assert "obsidian-context" in json.loads(target.read_text())["mcpServers"]
        target.write_text("{ broken", encoding="utf-8")
        assert client.post("/api/v1/scopes/s/claude-desktop/install", headers=headers).status_code == 409
        assert target.read_text() == "{ broken"


@pytest.mark.asyncio
async def test_desktop_entry_runs_scoped_proxy(vault_ctx) -> None:  # type: ignore[no-untyped-def]
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = _start_server(vault_ctx, port)
    (vault_ctx.data_dir / "runtime.json").write_text(json.dumps({"port": port}), encoding="utf-8")
    with TestClient(create_http_app(vault_ctx, admin_token="admin-secret")) as client:
        entry = client.get(
            "/api/v1/scopes/s/claude-config", headers={"Authorization": "Bearer admin-secret"}
        ).json()["claudeDesktop"]["config"]["mcpServers"]["obsidian-context"]
    try:
        # Exactly what Claude Desktop runs from claude_desktop_config.json.
        params = StdioServerParameters(
            command=entry["command"], args=entry["args"], env={**os.environ, **entry["env"]}
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            init = await session.initialize()
            assert init.serverInfo.name == "obsidian-context-vault"
            assert init.instructions and "scope_get_info" in init.instructions
            tools = {t.name for t in (await session.list_tools()).tools}
            assert {"scope_get_info", "docs_read_note"} <= tools
            note = await session.call_tool("docs_read_note", {"relativePath": "Allowed/Note.md"})
            assert not note.isError
            assert "hello from the vault" in json.dumps(note.model_dump())
    finally:
        server.should_exit = True


@pytest.mark.asyncio
async def test_proxy_rejects_wrong_token(vault_ctx, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    import subprocess
    import sys

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = _start_server(vault_ctx, port)
    (vault_ctx.data_dir / "runtime.json").write_text(json.dumps({"port": port}), encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "obsidian_context_mcp", "stdio-proxy", "--data-dir", str(vault_ctx.data_dir)],
            env={**os.environ, "OBSIDIAN_CONTEXT_SCOPE_TOKEN": "wrong"},
            input="", capture_output=True, text=True, timeout=60,
        )
        assert result.returncode == 1
        assert "MCP proxy failed" in result.stderr
        missing = subprocess.run(
            [sys.executable, "-m", "obsidian_context_mcp", "stdio-proxy", "--data-dir", str(tmp_path / "nope")],
            env={**os.environ, "OBSIDIAN_CONTEXT_SCOPE_TOKEN": "scope-secret"},
            input="", capture_output=True, text=True, timeout=60,
        )
        assert missing.returncode == 1
        assert "open Obsidian first" in missing.stderr
    finally:
        server.should_exit = True
