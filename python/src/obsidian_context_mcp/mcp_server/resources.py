"""MCP resources."""

from __future__ import annotations

import json
from urllib.parse import unquote

from obsidian_context_mcp.core.editor import Editor
from obsidian_context_mcp.core.project import detect_project_context
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.shared.types import SearchMode


async def read_resource(uri: str, project_root: str | None = None) -> str:
    ctx = detect_project_context(cli_root=project_root)
    if ctx is None:
        return json.dumps({"error": "project not found"})

    if uri.endswith("/status"):
        return json.dumps({
            "projectId": ctx.project_id,
            "status": ctx.get_status().value,
            "configured": ctx.configured,
        })

    if uri.endswith("/config"):
        config = ctx.config
        return json.dumps(config.model_dump() if config else {})

    if uri.endswith("/index-stats"):
        db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
        db.initialize()
        return json.dumps({"file_count": len(db.get_all_files())})

    if "/note/" in uri:
        encoded = uri.split("/note/")[-1]
        rel = unquote(encoded)
        editor = Editor(ctx)
        return json.dumps(editor.read_note(rel))

    if "/search/" in uri:
        encoded = uri.split("/search/")[-1]
        query = unquote(encoded)
        retriever = Retriever(ctx)
        results = retriever.search(query, mode=SearchMode.HYBRID)
        return json.dumps([r.model_dump() for r in results])

    return json.dumps({"error": "unknown resource"})
