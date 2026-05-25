"""Async index job queue."""

from __future__ import annotations

import threading

from obsidian_context_mcp.core.indexer import Indexer, ProgressCallback
from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.shared.types import IndexMode, IndexProgress, JobStatus


class IndexQueue:
    _instance: IndexQueue | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._jobs: dict[str, IndexProgress] = {}
        self._indexer: Indexer | None = None
        self._thread: threading.Thread | None = None

    @classmethod
    def get(cls) -> IndexQueue:
        with cls._lock:
            if cls._instance is None:
                cls._instance = IndexQueue()
            return cls._instance

    def get_status(self, job_id: str | None = None) -> IndexProgress | None:
        if job_id:
            return self._jobs.get(job_id)
        if self._jobs:
            return list(self._jobs.values())[-1]
        return None

    def start(
        self,
        ctx: ProjectContext,
        mode: IndexMode,
        callback: ProgressCallback | None = None,
    ) -> IndexProgress:
        for prog in self._jobs.values():
            if prog.status == JobStatus.RUNNING:
                return prog

        indexer = Indexer(ctx)
        self._indexer = indexer

        def _run() -> None:
            def _cb(p: IndexProgress) -> None:
                self._jobs[p.job_id] = p
                if callback:
                    callback(p)

            result = indexer.run(mode, progress_callback=_cb)
            self._jobs[result.job_id] = result

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        placeholder = IndexProgress(job_id="pending", status=JobStatus.RUNNING)
        self._jobs[placeholder.job_id] = placeholder
        return placeholder

    def cancel(self, job_id: str) -> bool:
        if self._indexer:
            self._indexer.cancel()
            return True
        return False
