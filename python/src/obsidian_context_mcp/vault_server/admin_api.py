"""Admin REST API for Obsidian plugin."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from obsidian_context_mcp.core.diagnostics import run_diagnostics_for_vault
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.llm_service import (
    DEFAULT_OLLAMA_HOST,
    LLM_PRESETS,
    LlmPullManager,
    ask_with_rag,
    list_installed_ollama_models,
    local_model_exists,
    ollama_health,
    ollama_model_available,
)
from obsidian_context_mcp.core.llm_local import list_local_models
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
        vault_files = scan_markdown_files(
            Path(self.vault_ctx.vault_real_path),
            include=self.vault_ctx.config.include,
            exclude=self.vault_ctx.config.exclude,
        )
        return JSONResponse(
            {
                "vaultId": self.vault_ctx.vault_id,
                "vaultPath": self.vault_ctx.vault_path,
                "indexStatus": self.vault_ctx.get_status().value,
                "fileCount": len(db.get_all_files()),
                "vaultFileCount": len(vault_files),
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

    async def index_file(self, request: Request) -> Response:
        body = await request.json()
        rel = body.get("relativePath") or body.get("relative_path")
        if not rel or not isinstance(rel, str):
            return JSONResponse({"error": "relativePath required"}, status_code=400)
        rel_norm = rel.replace("\\", "/").lstrip("/")
        try:
            await asyncio.to_thread(Indexer(self.vault_ctx).index_file, rel_norm)
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
        return JSONResponse({"ok": True, "relativePath": rel_norm})

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

    async def llm_presets(self, _request: Request) -> Response:
        return JSONResponse(
            {
                "presets": LLM_PRESETS,
                "defaultHost": DEFAULT_OLLAMA_HOST,
                "defaultBackend": "local",
            }
        )

    async def llm_status(self, request: Request) -> Response:
        backend = request.query_params.get("backend", "local")
        host = request.query_params.get("host", DEFAULT_OLLAMA_HOST)
        model = request.query_params.get("model", "")
        data_dir = self.vault_ctx.data_dir

        if backend == "local":
            health = {"ok": True, "backend": "local"}
            installed = await asyncio.to_thread(list_local_models, data_dir)
            available = (
                await asyncio.to_thread(local_model_exists, data_dir, model) if model else False
            )
        else:
            health = await asyncio.to_thread(ollama_health, host)
            installed = []
            available = False
            if health.get("ok"):
                try:
                    installed = await asyncio.to_thread(list_installed_ollama_models, host)
                    if model:
                        available = await asyncio.to_thread(
                            ollama_model_available, host, model
                        )
                except Exception as exc:
                    health["error"] = str(exc)

        pull = LlmPullManager.get().get_progress()
        return JSONResponse(
            {
                "health": health,
                "installedModels": installed,
                "modelAvailable": available,
                "pull": pull,
                "backend": backend,
            }
        )

    async def llm_pull(self, request: Request) -> Response:
        body = await request.json()
        backend = body.get("backend", "local")
        host = body.get("host", DEFAULT_OLLAMA_HOST)
        model = body.get("model", "")
        if not model:
            return JSONResponse({"error": "model required"}, status_code=400)

        if backend == "local":
            progress = await asyncio.to_thread(
                LlmPullManager.get().start_local_pull,
                self.vault_ctx.data_dir,
                model,
            )
        else:
            progress = await asyncio.to_thread(
                LlmPullManager.get().start_ollama_pull, host, model
            )
        return JSONResponse(progress)

    async def llm_pull_status(self, _request: Request) -> Response:
        return JSONResponse(LlmPullManager.get().get_progress())

    async def llm_ask(self, request: Request) -> Response:
        body = await request.json()
        query = body.get("query", "").strip()
        backend = body.get("backend", "local")
        host = body.get("host", DEFAULT_OLLAMA_HOST)
        model = body.get("model", "")
        if not query:
            return JSONResponse({"error": "query required"}, status_code=400)
        if not model:
            return JSONResponse({"error": "model required"}, status_code=400)

        if backend == "local":
            if not await asyncio.to_thread(local_model_exists, self.vault_ctx.data_dir, model):
                return JSONResponse(
                    {"error": f"Model {model} not downloaded. Select it in plugin settings."},
                    status_code=400,
                )
        elif not await asyncio.to_thread(ollama_model_available, host, model):
            return JSONResponse(
                {"error": f"Model {model} not in Ollama. Download it first."},
                status_code=400,
            )

        try:
            result = await asyncio.to_thread(
                ask_with_rag,
                self.vault_ctx,
                query,
                model,
                backend=backend,
                host=host,
                data_dir=self.vault_ctx.data_dir,
                top_k=int(body.get("topK", 8)),
            )
            return JSONResponse(result.to_dict())
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=500)
