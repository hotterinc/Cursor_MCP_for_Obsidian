"""Admin REST API for Obsidian plugin."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from obsidian_context_mcp.core.diagnostics import run_diagnostics_for_vault
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.core.scope_filter import filter_paths
from obsidian_context_mcp.core.scope_store import generate_scope_token
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import scan_markdown_files
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.shared.types import AccessScope, IndexMode
from obsidian_context_mcp.vault_server.index_queue import VaultIndexQueue


@dataclass
class AdminApi:
    vault_ctx: VaultContext

    async def health(self, _request: Request) -> Response:
        return JSONResponse({"ok": True, "vaultId": self.vault_ctx.vault_id})

    async def status(self, _request: Request) -> Response:
        db = SQLiteStore(self.vault_ctx.work_context().db_path)
        db.initialize()
        prog = VaultIndexQueue.get().get_status()
        return JSONResponse(
            {
                "vaultId": self.vault_ctx.vault_id,
                "vaultPath": self.vault_ctx.vault_path,
                "indexStatus": self.vault_ctx.get_status().value,
                "fileCount": len(db.get_all_files()),
                "job": prog.model_dump() if prog else None,
            }
        )

    async def search(self, request: Request) -> Response:
        body = await request.json()
        retriever = Retriever(self.vault_ctx)
        from obsidian_context_mcp.shared.types import SearchMode

        results = retriever.search(
            body["query"],
            top_k=body.get("topK", 10),
            mode=SearchMode(body.get("mode", "hybrid")),
        )
        return JSONResponse({"results": [r.model_dump() for r in results]})

    async def reindex(self, request: Request) -> Response:
        body = await request.json() if request.headers.get("content-type") else {}
        mode = IndexMode.FULL if body.get("mode") == "full" else IndexMode.INCREMENTAL
        progress = VaultIndexQueue.get().start(self.vault_ctx, mode)
        return JSONResponse(progress.model_dump())

    async def list_scopes(self, _request: Request) -> Response:
        scopes = self.vault_ctx.scope_store.list_scopes()
        safe = []
        for s in scopes:
            item = s.model_dump(by_alias=True)
            item["tokenPreview"] = s.token[:12] + "..." if s.token else ""
            safe.append(item)
        return JSONResponse({"scopes": safe})

    async def upsert_scope(self, request: Request) -> Response:
        body = await request.json()
        scope = AccessScope.model_validate(body)
        if not scope.token:
            scope.token = generate_scope_token()
        saved = self.vault_ctx.scope_store.upsert(scope)
        return JSONResponse(saved.model_dump(by_alias=True))

    async def delete_scope(self, request: Request) -> Response:
        scope_id = request.path_params["scope_id"]
        ok = self.vault_ctx.scope_store.delete(scope_id)
        return JSONResponse({"ok": ok})

    async def regenerate_token(self, request: Request) -> Response:
        scope_id = request.path_params["scope_id"]
        scope = self.vault_ctx.scope_store.regenerate_token(scope_id)
        if scope is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse(scope.model_dump(by_alias=True))

    async def scope_preview(self, request: Request) -> Response:
        body = await request.json()
        scope = AccessScope.model_validate(body)
        files = scan_markdown_files(
            Path(self.vault_ctx.vault_real_path),
            include=self.vault_ctx.config.include,
            exclude=self.vault_ctx.config.exclude,
        )
        allowed = filter_paths(files, scope)
        return JSONResponse({"fileCount": len(allowed), "sample": allowed[:20]})

    async def cursor_config(self, request: Request) -> Response:
        scope_id = request.path_params["scope_id"]
        scope = self.vault_ctx.scope_store.get_by_id(scope_id)
        if scope is None:
            return JSONResponse({"error": "not found"}, status_code=404)
        host = request.query_params.get("host", "127.0.0.1")
        port = request.query_params.get("port", "0")
        runtime_path = self.vault_ctx.data_dir / "runtime.json"
        if runtime_path.exists():
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            port = str(runtime.get("port", port))
        config = {
            "mcpServers": {
                "obsidian-context": {
                    "url": f"http://{host}:{port}/sse",
                    "headers": {"Authorization": f"Bearer {scope.token}"},
                }
            }
        }
        return JSONResponse({"config": config, "scope": scope.model_dump(by_alias=True)})

    async def diagnostics(self, _request: Request) -> Response:
        checks = run_diagnostics_for_vault(self.vault_ctx)
        return JSONResponse({"checks": [c.model_dump() for c in checks]})

    async def get_config(self, _request: Request) -> Response:
        return JSONResponse(self.vault_ctx.config.model_dump())

    async def update_config(self, request: Request) -> Response:
        body = await request.json()
        config = self.vault_ctx.config_store.create_or_update(
            self.vault_ctx.vault_path,
            include=body.get("include"),
            exclude=body.get("exclude"),
            embedding_provider=body.get("embeddingProvider"),
            embedding_model=body.get("embeddingModel"),
            watcher_enabled=body.get("watcherEnabled"),
        )
        self.vault_ctx.config = config
        return JSONResponse(config.model_dump())
