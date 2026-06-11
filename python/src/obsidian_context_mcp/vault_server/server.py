"""Vault-server entry point (Obsidian plugin sidecar)."""

from __future__ import annotations

import json
import os
import signal
import socket
import threading
from datetime import datetime
from pathlib import Path

import uvicorn
from loguru import logger

from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.locks import RuntimeLock
from obsidian_context_mcp.core.logging import setup_logging
from obsidian_context_mcp.core.ml_runtime import configure_ml_runtime
from obsidian_context_mcp.core.vault_context import VaultContext, get_vault_context
from obsidian_context_mcp.core.vault_paths import get_runtime_path
from obsidian_context_mcp.core.watcher import VaultWatcher
from obsidian_context_mcp.shared.constants import DEFAULT_VAULT_SERVER_HOST
from obsidian_context_mcp.shared.types import IndexMode, VaultRuntimeInfo
from obsidian_context_mcp.vault_server.http_app import create_http_app
from obsidian_context_mcp.vault_server.index_queue import VaultIndexQueue


def _pick_free_port(host: str) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((host, 0))
        return int(s.getsockname()[1])


def _write_runtime(data_dir: Path, *, port: int, host: str, vault_id: str) -> None:
    info = VaultRuntimeInfo(
        port=port,
        pid=os.getpid(),
        host=host,
        status="running",
        started_at=datetime.utcnow().isoformat() + "Z",
        vault_id=vault_id,
    )
    get_runtime_path(data_dir).write_text(
        info.model_dump_json(by_alias=True, indent=2), encoding="utf-8"
    )


def _clear_runtime(data_dir: Path) -> None:
    path = get_runtime_path(data_dir)
    if path.exists():
        path.unlink()


def run_vault_server(
    vault_path: str,
    data_dir: str,
    *,
    host: str = DEFAULT_VAULT_SERVER_HOST,
    port: int = 0,
) -> None:
    configure_ml_runtime()
    resolved_data = Path(data_dir).resolve()
    ctx = get_vault_context(vault_path, data_dir=resolved_data)
    setup_logging(log_file=ctx.data_dir / "logs" / "vault-server.log")

    lock_name = f"vault-server-{ctx.vault_id[:16]}"
    runtime_lock = RuntimeLock(lock_name, timeout=3)
    try:
        runtime_lock.acquire()
    except Exception:
        logger.error("Another vault-server is already running for this vault")
        raise SystemExit(1) from None

    chosen_port = port if port > 0 else _pick_free_port(host)
    _write_runtime(resolved_data, port=chosen_port, host=host, vault_id=ctx.vault_id)

    def _shutdown(*_args: object) -> None:
        _clear_runtime(resolved_data)
        runtime_lock.release()
        os._exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    watcher = VaultWatcher(ctx)
    watcher.start()

    def _initial_index() -> None:
        db_path = ctx.work_context().db_path
        if not db_path.exists() or db_path.stat().st_size == 0:
            VaultIndexQueue.get().start(ctx, IndexMode.INCREMENTAL)
        else:
            indexer = Indexer(ctx)
            indexer.run(IndexMode.INCREMENTAL)

    threading.Thread(target=_initial_index, daemon=True).start()

    app = create_http_app(ctx)
    logger.info("Vault server listening on http://{}:{}", host, chosen_port)
    try:
        uvicorn.run(app, host=host, port=chosen_port, log_level="info")
    finally:
        watcher.stop()
        _clear_runtime(resolved_data)
        runtime_lock.release()
