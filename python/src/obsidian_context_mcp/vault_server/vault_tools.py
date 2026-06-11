"""Vault-scoped MCP tool handlers."""

from __future__ import annotations

import json
from typing import Any

from obsidian_context_mcp.core.context_pack import build_context_pack
from obsidian_context_mcp.core.diagnostics import run_diagnostics_for_vault
from obsidian_context_mcp.core.editor import Editor
from obsidian_context_mcp.core.errors import ScopeAccessDeniedError
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.core.scope_filter import filter_paths, path_in_scope
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import scan_markdown_files
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.vault_server.auth import require_vault_context
from obsidian_context_mcp.vault_server.index_queue import VaultIndexQueue
from obsidian_context_mcp.shared.types import IndexMode, PatchMode, SearchMode


def _scoped_ctx() -> VaultContext:
    base = require_vault_context()
    if base.scope is None:
        raise ScopeAccessDeniedError(
            "Missing or invalid scope token. Configure Authorization: Bearer <scope-token> in Cursor MCP."
        )
    return base


async def scope_get_info(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    scope = ctx.scope
    assert scope is not None
    db = SQLiteStore(ctx.work_context().db_path)
    db.initialize()
    vault_root = ctx.vault_real_path
    from pathlib import Path

    all_files = scan_markdown_files(
        Path(vault_root),
        include=ctx.config.include,
        exclude=ctx.config.exclude,
    )
    allowed = filter_paths(all_files, scope)
    return {
        "vaultId": ctx.vault_id,
        "scopeId": scope.id,
        "scopeName": scope.name,
        "include": scope.include,
        "exclude": scope.exclude,
        "writeAccess": scope.write_access,
        "canReindex": scope.can_reindex,
        "indexStatus": ctx.get_status().value,
        "allowedFileCount": len(allowed),
        "totalIndexedFiles": len(db.get_all_files()),
    }


async def docs_reindex(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    if not ctx.scope or not ctx.scope.can_reindex:
        raise ScopeAccessDeniedError("This scope cannot trigger reindex")
    mode = IndexMode.FULL if args.get("mode") == "full" else IndexMode.INCREMENTAL
    progress = VaultIndexQueue.get().start(ctx, mode)
    return progress.model_dump()


async def docs_index_status(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    prog = VaultIndexQueue.get().get_status()
    return {
        "status": ctx.get_status().value,
        "job": prog.model_dump() if prog else None,
    }


async def docs_search(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
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
    ctx = _scoped_ctx()
    pack = build_context_pack(
        ctx,
        args["task"],
        token_budget=args.get("tokenBudget", 6000),
        top_k=args.get("topK", 12),
    )
    return pack.model_dump()


async def docs_read_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    editor = Editor(ctx)
    note = editor.read_note(args["relativePath"])
    return {
        "relativePath": note["relative_path"],
        "sha256": note["sha256"],
        "content": note["content"],
        "frontmatter": note["frontmatter"],
        "headings": note["headings"],
    }


async def docs_list_notes(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    db = SQLiteStore(ctx.work_context().db_path)
    db.initialize()
    notes = db.list_notes(
        query=args.get("query"),
        tag=args.get("tag"),
        limit=args.get("limit", 50),
    )
    scope = ctx.scope
    if scope:
        notes = [n for n in notes if path_in_scope(n.get("relative_path", ""), scope)]
    return {"notes": notes}


async def docs_patch_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    editor = Editor(ctx)
    result = editor.patch_note(
        args["relativePath"],
        args["expectedSha256"],
        PatchMode(args["mode"]),
        args["patch"],
        dry_run=args.get("dryRun", False),
        create_backup_flag=args.get("createBackup", True),
    )
    return {
        "relativePath": result.relative_path,
        "oldSha256": result.old_sha256,
        "newSha256": result.new_sha256,
        "backupPath": result.backup_path,
        "dryRun": result.dry_run,
    }


async def docs_create_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    editor = Editor(ctx)
    result = editor.create_note(
        args["relativePath"],
        args["content"],
        overwrite=args.get("overwrite", False),
        create_backup_flag=args.get("createBackup", True),
    )
    return {
        "relativePath": result.relative_path,
        "oldSha256": result.old_sha256,
        "newSha256": result.new_sha256,
        "backupPath": result.backup_path,
        "dryRun": result.dry_run,
    }


async def docs_delete_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    editor = Editor(ctx)
    result = editor.delete_note(
        args["relativePath"],
        args["expectedSha256"],
        create_backup_flag=args.get("createBackup", True),
    )
    return {
        "relativePath": result.relative_path,
        "oldSha256": result.old_sha256,
        "newSha256": result.new_sha256,
        "backupPath": result.backup_path,
        "dryRun": result.dry_run,
    }


async def docs_rename_note(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    editor = Editor(ctx)
    result = editor.rename_note(
        args["fromRelativePath"],
        args["toRelativePath"],
        args["expectedSha256"],
        create_backup_flag=args.get("createBackup", True),
    )
    return {
        "relativePath": result.relative_path,
        "oldSha256": result.old_sha256,
        "newSha256": result.new_sha256,
        "backupPath": result.backup_path,
        "dryRun": result.dry_run,
    }


async def diagnostics_run(args: dict[str, Any]) -> dict[str, Any]:
    ctx = _scoped_ctx()
    checks = run_diagnostics_for_vault(ctx)
    return {"checks": [c.model_dump() for c in checks]}


VAULT_TOOL_HANDLERS = {
    "scope_get_info": scope_get_info,
    "docs_reindex": docs_reindex,
    "docs_index_status": docs_index_status,
    "docs_search": docs_search,
    "docs_get_context_pack": docs_get_context_pack,
    "docs_read_note": docs_read_note,
    "docs_list_notes": docs_list_notes,
    "docs_patch_note": docs_patch_note,
    "docs_create_note": docs_create_note,
    "docs_delete_note": docs_delete_note,
    "docs_rename_note": docs_rename_note,
    "diagnostics_run": diagnostics_run,
}
