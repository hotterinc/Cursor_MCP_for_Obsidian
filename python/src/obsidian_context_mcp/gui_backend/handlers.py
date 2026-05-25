"""GUI backend RPC handlers."""

from __future__ import annotations

from obsidian_context_mcp.core.app_paths import get_app_data_dir
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
from obsidian_context_mcp.core.watcher import VaultWatcher
from obsidian_context_mcp.gui_backend.schemas import (
    IndexStartParams,
    ListNotesParams,
    ReadNoteParams,
    SearchParams,
    SettingsUpdateParams,
    VaultSaveParams,
    VaultValidateParams,
)
from obsidian_context_mcp.shared.types import IndexMode


def _ctx(params: dict, *, require_configured: bool = False) -> ProjectContext:
    root = params.get("project_root") or params.get("projectRoot")
    ctx = detect_project_context(cli_root=root)
    if ctx is None:
        raise ValueError("Project root not found")
    if require_configured and not ctx.configured:
        raise ValueError("Project not configured")
    return ctx


def handle_project_get_current(params: dict) -> dict:
    ctx = _ctx(params)
    config = ctx.config
    return {
        "projectId": ctx.project_id,
        "projectRoot": ctx.project_root,
        "projectRealPath": ctx.project_real_path,
        "projectName": ctx.project_name,
        "configured": ctx.configured,
        "vaultPath": config.vault_path if config else None,
        "status": ctx.get_status().value,
        "writeAccess": config.write_access if config else False,
    }


def handle_project_set_root(params: dict) -> dict:
    root = params.get("project_root") or params.get("projectRoot")
    if not root:
        raise ValueError("project_root required")
    ctx = get_project_context(root)
    return handle_project_get_current({"project_root": ctx.project_root})


def handle_vault_validate_path(params: dict) -> dict:
    p = VaultValidateParams.model_validate(params)
    result = validate_vault_path(p.vault_path)
    return {
        "canceled": False,
        "vaultPath": result.vault_path,
        "realPath": result.real_path,
        "markdownFilesCount": result.markdown_files_count,
        "warnings": result.warnings,
        "canRead": result.can_read,
        "canWrite": result.can_write,
    }


def handle_vault_save_config(params: dict) -> dict:
    p = VaultSaveParams.model_validate(params)
    validation = validate_vault_path(
        p.vault_path,
        include=p.include,
        exclude=p.exclude,
    )
    ctx = get_project_context(p.project_root)
    config = ctx.config_store.create_or_update(
        p.project_root,
        vault_path=validation.vault_path,
        write_access=p.write_access,
        backup_before_edit=p.backup_before_edit,
        include=p.include,
        exclude=p.exclude,
    )
    VaultWatcher.get(ctx).start()
    return {"ok": True, "config": config.model_dump()}


def handle_index_status(params: dict) -> dict:
    ctx = _ctx(params)
    prog = IndexQueue.get().get_status()
    return {
        "status": ctx.get_status().value,
        "progress": prog.model_dump() if prog else None,
    }


def handle_index_start(params: dict) -> dict:
    p = IndexStartParams.model_validate(params)
    ctx = _ctx(p.model_dump(), require_configured=True)
    mode = IndexMode.FULL if p.mode == "full" else IndexMode.INCREMENTAL

    def _cb(progress):
        from obsidian_context_mcp.gui_backend.server import get_rpc_server
        srv = get_rpc_server()
        if srv:
            srv.emit_event("index.progress", progress.model_dump())

    prog = IndexQueue.get().start(ctx, mode, callback=_cb)
    return {"jobId": prog.job_id, "status": prog.status.value}


def handle_index_cancel(params: dict) -> dict:
    job_id = params.get("job_id") or params.get("jobId", "")
    ok = IndexQueue.get().cancel(job_id)
    return {"ok": ok}


def handle_search_docs(params: dict) -> dict:
    p = SearchParams.model_validate(params)
    ctx = _ctx(p.model_dump(), require_configured=True)
    retriever = Retriever(ctx)
    results = retriever.search(p.query, top_k=p.top_k, mode=p.mode)
    return {"results": [r.model_dump() for r in results]}


def handle_notes_read(params: dict) -> dict:
    p = ReadNoteParams.model_validate(params)
    ctx = _ctx(p.model_dump(), require_configured=True)
    editor = Editor(ctx)
    return editor.read_note(p.relative_path)


def handle_notes_list(params: dict) -> dict:
    p = ListNotesParams.model_validate(params)
    ctx = _ctx(p.model_dump(), require_configured=True)
    db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
    db.initialize()
    notes = db.list_notes(query=p.query, tag=p.tag, limit=p.limit)
    return {"notes": notes}


def handle_diagnostics_run(params: dict) -> dict:
    ctx = _ctx(params)
    checks = run_diagnostics(ctx)
    return {"checks": [c.model_dump() for c in checks]}


def handle_settings_get(params: dict) -> dict:
    ctx = _ctx(params)
    config = ctx.config
    return {
        "projectRoot": ctx.project_root,
        "vaultPath": config.vault_path if config else None,
        "writeAccess": config.write_access if config else False,
        "backupBeforeEdit": config.backup_before_edit if config else True,
        "embeddingProvider": config.embedding_provider if config else "sentence-transformers",
        "embeddingModel": config.embedding_model if config else "intfloat/multilingual-e5-small",
        "include": config.include if config else [],
        "exclude": config.exclude if config else [],
        "watcherEnabled": config.watcher_enabled if config else True,
        "appDataPath": str(get_app_data_dir()),
    }


def handle_settings_update(params: dict) -> dict:
    p = SettingsUpdateParams.model_validate(params)
    ctx = _ctx(p.model_dump())
    config = ctx.config_store.create_or_update(
        ctx.project_root,
        write_access=p.write_access,
        backup_before_edit=p.backup_before_edit,
        watcher_enabled=p.watcher_enabled,
        embedding_provider=p.embedding_provider,
        embedding_model=p.embedding_model,
        include=p.include,
        exclude=p.exclude,
    )
    return {"ok": True, "config": config.model_dump()}


def handle_app_open_vault_path_request(params: dict) -> dict:
    ctx = _ctx(params, require_configured=True)
    config = ctx.config_store.require_configured()
    return {
        "absolutePath": config.vault_path,
        "realPath": config.vault_real_path,
        "intent": "open_vault_folder",
    }


def handle_app_open_app_data_path_request(params: dict) -> dict:
    ctx = _ctx(params)
    from obsidian_context_mcp.core.app_paths import get_project_dir
    return {
        "absolutePath": str(get_project_dir(ctx.project_id)),
        "intent": "open_app_data_folder",
    }
