"""MCP tool handlers."""

from __future__ import annotations

import json
from typing import Any

from obsidian_context_mcp.core.app_paths import get_open_request_path
from obsidian_context_mcp.core.context_pack import build_context_pack
from obsidian_context_mcp.core.diagnostics import run_diagnostics
from obsidian_context_mcp.core.editor import Editor
from obsidian_context_mcp.core.index_queue import IndexQueue
from obsidian_context_mcp.core.project import (
    ProjectContext,
    detect_project_context,
    get_project_context,
)
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import validate_vault_path
from obsidian_context_mcp.shared.types import IndexMode, PatchMode, SearchMode


def _ctx(project_root: str | None) -> ProjectContext:
    ctx = detect_project_context(cli_root=project_root)
    if ctx is None:
        raise ValueError("Project root not found")
    return ctx


async def config_get_project(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    config = ctx.config
    db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
    stats = {}
    if config and config.configured:
        db.initialize()
        stats = {"file_count": len(db.get_all_files())}
    return {
        "projectId": ctx.project_id,
        "projectRoot": ctx.project_root,
        "projectName": ctx.project_name,
        "vaultPath": config.vault_path if config else None,
        "configured": ctx.configured,
        "writeAccess": config.write_access if config else False,
        "status": ctx.get_status().value,
        "indexStats": stats,
    }


async def config_set_vault_path(args: dict[str, Any]) -> dict[str, Any]:
    ctx = get_project_context(args["projectRoot"])
    validation = validate_vault_path(
        args["vaultPath"],
        include=args.get("include"),
        exclude=args.get("exclude"),
    )
    config = ctx.config_store.create_or_update(
        args["projectRoot"],
        vault_path=validation.vault_path,
        write_access=args.get("writeAccess", False),
        include=args.get("include"),
        exclude=args.get("exclude"),
    )
    return {"ok": True, "config": config.model_dump()}


async def config_open_gui(args: dict[str, Any]) -> dict[str, Any]:
    project_root = args.get("projectRoot")
    req_path = get_open_request_path()
    req_path.write_text(json.dumps({"projectRoot": project_root}), encoding="utf-8")
    return {
        "ok": True,
        "opened": False,
        "message": "Desktop app open request written. Launch Electron GUI or run: pnpm dev:desktop",
        "projectRoot": project_root,
    }


async def docs_reindex(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    mode = IndexMode.FULL if args.get("mode") == "full" else IndexMode.INCREMENTAL
    progress = IndexQueue.get().start(ctx, mode)
    return progress.model_dump()


async def docs_index_status(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    prog = IndexQueue.get().get_status()
    return {
        "status": ctx.get_status().value,
        "job": prog.model_dump() if prog else None,
    }


async def docs_search(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    retriever = Retriever(ctx)
    mode = SearchMode(args.get("mode", "hybrid"))
    results = retriever.search(
        args["query"],
        top_k=args.get("topK", 10),
        mode=mode,
        filters=args.get("filters"),
    )
    return {"results": [r.model_dump() for r in results]}


async def docs_get_context_pack(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    pack = build_context_pack(
        ctx,
        args["task"],
        token_budget=args.get("tokenBudget", 6000),
        top_k=args.get("topK", 12),
        include_linked=args.get("includeLinked", True),
        include_frontmatter=args.get("includeFrontmatter", True),
    )
    return pack.model_dump()


async def docs_read_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    editor = Editor(ctx)
    return editor.read_note(args["relativePath"])


async def docs_list_notes(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
    db.initialize()
    notes = db.list_notes(
        query=args.get("query"),
        tag=args.get("tag"),
        limit=args.get("limit", 50),
    )
    return {"notes": notes}


async def docs_patch_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    editor = Editor(ctx)
    result = editor.patch_note(
        args["relativePath"],
        args["expectedSha256"],
        PatchMode(args["mode"]),
        args["patch"],
        dry_run=args.get("dryRun", False),
        create_backup_flag=args.get("createBackup", True),
    )
    return result.__dict__


async def docs_create_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    editor = Editor(ctx)
    result = editor.create_note(
        args["relativePath"],
        args["content"],
        overwrite=args.get("overwrite", False),
        create_backup_flag=args.get("createBackup", True),
    )
    return result.__dict__


async def docs_delete_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    editor = Editor(ctx)
    result = editor.delete_note(
        args["relativePath"],
        args["expectedSha256"],
        create_backup_flag=args.get("createBackup", True),
    )
    return result.__dict__


async def docs_rename_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    editor = Editor(ctx)
    result = editor.rename_note(
        args["fromRelativePath"],
        args["toRelativePath"],
        args["expectedSha256"],
        create_backup_flag=args.get("createBackup", True),
    )
    return result.__dict__


async def diagnostics_run(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _ctx(args.get("projectRoot"))
    checks = run_diagnostics(ctx)
    return {"checks": [c.model_dump() for c in checks]}
