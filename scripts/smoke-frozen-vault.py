"""Exercise a frozen sidecar against an isolated vault and its MCP endpoint."""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from obsidian_context_mcp.core.scope_store import ScopeStore
from obsidian_context_mcp.core.vault_config_store import VaultConfigStore
from obsidian_context_mcp.shared.types import AccessScope


def main(binary: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="obsidian-frozen-smoke-") as temporary:
        root = Path(temporary)
        vault = root / "vault"
        vault.mkdir()
        (vault / "One.md").write_text("# Frozen test\nA searchable note.\n", encoding="utf-8")
        data = root / "data"
        VaultConfigStore(data).create_or_update(str(vault), embedding_provider="fake", watcher_enabled=False)
        ScopeStore(data).upsert(AccessScope(id="smoke", name="Smoke", include=["**/*.md"], token="smoke-scope-token"))
        env = os.environ.copy()
        env.update(HF_HUB_OFFLINE="1", ANONYMIZED_TELEMETRY="False", OBSIDIAN_CONTEXT_DATA_DIR=str(data))
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        process = subprocess.Popen(
            [str(binary), "vault-server", "--vault-path", str(vault), "--data-dir", str(data)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env, creationflags=flags,
        )
        runtime: dict[str, Any] | None = None
        try:
            deadline = time.monotonic() + 180
            with httpx.Client(timeout=5) as client:
                while time.monotonic() < deadline:
                    if process.poll() is not None:
                        raise RuntimeError(f"Frozen sidecar exited early: {process.returncode}")
                    path = data / "runtime.json"
                    if path.exists():
                        try:
                            runtime = json.loads(path.read_text(encoding="utf-8"))
                            base = f"http://127.0.0.1:{runtime['port']}"
                            admin = {"Authorization": f"Bearer {runtime['adminToken']}"}
                            status = client.get(base + "/api/v1/status", headers=admin)
                            if status.status_code == 200:
                                payload = status.json()
                                job = payload.get("job") or {}
                                if job.get("status") == "failed":
                                    raise RuntimeError(f"Frozen indexing failed: {job}")
                                if payload["fileCount"] >= 1 and job.get("status") == "completed":
                                    break
                        except (OSError, ValueError, KeyError, httpx.HTTPError):
                            pass
                    time.sleep(.25)
                else:
                    raise TimeoutError("Frozen vault did not complete indexing")

                headers = {"Authorization": "Bearer smoke-scope-token", "Accept": "application/json, text/event-stream"}
                def rpc(method: str, params: dict[str, Any], request_id: int) -> dict[str, Any]:
                    response = client.post(base + "/mcp", headers=headers, json={"jsonrpc": "2.0", "id": request_id, "method": method, "params": params})
                    response.raise_for_status()
                    result = response.json()
                    if "error" in result:
                        raise RuntimeError(str(result["error"]))
                    return result["result"]

                rpc("initialize", {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "frozen-smoke", "version": "1"}}, 1)
                tools = rpc("tools/list", {}, 2)["tools"]
                assert any(item["name"] == "docs_read_note" for item in tools)
                result = rpc("tools/call", {"name": "docs_read_note", "arguments": {"relativePath": "One.md"}}, 3)
                assert not result.get("isError"), result
                assert "A searchable note" in result["content"][0]["text"]
                print("Frozen vault indexing and MCP read passed")
        finally:
            if runtime and isinstance(runtime.get("pid"), int):
                try:
                    os.kill(runtime["pid"], signal.SIGTERM)
                except OSError:
                    pass
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    main(Path(sys.argv[1]).resolve())
