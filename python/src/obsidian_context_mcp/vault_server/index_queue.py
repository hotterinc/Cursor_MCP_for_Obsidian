"""Background indexing for vault-server."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.shared.types import IndexMode, IndexProgress, JobStatus

if TYPE_CHECKING:
    pass


class VaultIndexQueue:
    _instance: VaultIndexQueue | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._progress: IndexProgress | None = None
        self._indexer: Indexer | None = None

    @classmethod
    def get(cls) -> VaultIndexQueue:
        with cls._lock:
            if cls._instance is None:
                cls._instance = VaultIndexQueue()
            return cls._instance

    def get_status(self) -> IndexProgress | None:
        return self._progress

    def start(self, ctx: VaultContext, mode: IndexMode = IndexMode.INCREMENTAL) -> IndexProgress:
        if self._thread and self._thread.is_alive():
            return self._progress or IndexProgress(job_id="active", status=JobStatus.RUNNING)

        self._indexer = Indexer(ctx)
        job_holder: list[IndexProgress] = []

        def _run() -> None:
            def on_progress(p: IndexProgress) -> None:
                self._progress = p

            result = self._indexer.run(mode, progress_callback=on_progress)  # type: ignore[union-attr]
            self._progress = result

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return IndexProgress(job_id="starting", status=JobStatus.RUNNING)

    def cancel(self) -> None:
        if self._indexer:
            self._indexer.cancel()
