"""GUI backend stdio server."""

from __future__ import annotations

from obsidian_context_mcp.core.logging import get_logger, setup_logging
from obsidian_context_mcp.core.project import get_project_context
from obsidian_context_mcp.gui_backend import handlers
from obsidian_context_mcp.gui_backend.rpc import JsonRpcServer

_rpc_server: JsonRpcServer | None = None
logger = get_logger()


def get_rpc_server() -> JsonRpcServer | None:
    return _rpc_server


def run_gui_backend(project_root: str) -> None:
    global _rpc_server
    ctx = get_project_context(project_root)
    setup_logging(
        level="INFO",
        log_file=ctx.config_store.config_path.parent / "logs" / "gui-backend.log",
    )
    logger.info("GUI backend starting for project {}", ctx.project_id)

    rpc = JsonRpcServer()
    _rpc_server = rpc

    rpc.register("project.getCurrent", handlers.handle_project_get_current)
    rpc.register("project.setRoot", handlers.handle_project_set_root)
    rpc.register("vault.validatePath", handlers.handle_vault_validate_path)
    rpc.register("vault.saveConfig", handlers.handle_vault_save_config)
    rpc.register("index.status", handlers.handle_index_status)
    rpc.register("index.start", handlers.handle_index_start)
    rpc.register("index.cancel", handlers.handle_index_cancel)
    rpc.register("search.docs", handlers.handle_search_docs)
    rpc.register("notes.read", handlers.handle_notes_read)
    rpc.register("notes.list", handlers.handle_notes_list)
    rpc.register("diagnostics.run", handlers.handle_diagnostics_run)
    rpc.register("settings.get", handlers.handle_settings_get)
    rpc.register("settings.update", handlers.handle_settings_update)
    rpc.register("app.openVaultPathRequest", handlers.handle_app_open_vault_path_request)
    rpc.register("app.openAppDataPathRequest", handlers.handle_app_open_app_data_path_request)

    rpc.serve_stdio()
