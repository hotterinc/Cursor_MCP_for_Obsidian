"""Watchdog-based vault file watcher."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.shared.constants import WATCHER_DEBOUNCE_MS_DEFAULT


class VaultWatcherHandler(FileSystemEventHandler):
    def __init__(
        self,
        ctx: ProjectContext,
        *,
        debounce_ms: int = WATCHER_DEBOUNCE_MS_DEFAULT,
        on_event: Callable[[str, str], None] | None = None,
    ) -> None:
        super().__init__()
        self.ctx = ctx
        self.debounce_ms = debounce_ms
        self.on_event = on_event
        self._pending: dict[str, threading.Timer] = {}
        self._lock = threading.Lock()
        self._indexer = Indexer(ctx)

    def _schedule(self, rel: str, event_type: str) -> None:
        with self._lock:
            if rel in self._pending:
                self._pending[rel].cancel()

            def _process() -> None:
                try:
                    if event_type == "deleted":
                        self._indexer.index_file(rel)
                    else:
                        self._indexer.index_file(rel)
                    if self.on_event:
                        self.on_event(event_type, rel)
                except Exception:
                    pass
                with self._lock:
                    self._pending.pop(rel, None)

            timer = threading.Timer(self.debounce_ms / 1000.0, _process)
            self._pending[rel] = timer
            timer.start()

    def _rel_path(self, src_path: str) -> str | None:
        vault = Path(self.ctx.config.vault_real_path or "")
        try:
            rel = Path(src_path).resolve().relative_to(vault.resolve())
        except ValueError:
            return None
        rel_str = rel.as_posix()
        if not rel_str.lower().endswith(".md"):
            return None
        for prefix in (".obsidian/", ".git/", "node_modules/", ".trash/"):
            if rel_str.startswith(prefix):
                return None
        return rel_str

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel_path(event.src_path)
        if rel:
            self._schedule(rel, "created")

    def on_modified(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel_path(event.src_path)
        if rel:
            self._schedule(rel, "modified")

    def on_deleted(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        rel = self._rel_path(event.src_path)
        if rel:
            self._schedule(rel, "deleted")

    def on_moved(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        src_rel = self._rel_path(event.src_path)
        dest_rel = self._rel_path(event.dest_path) if event.dest_path else None
        if src_rel:
            self._schedule(src_rel, "deleted")
        if dest_rel:
            self._schedule(dest_rel, "created")


class VaultWatcher:
    _instances: dict[str, VaultWatcher] = {}

    def __init__(self, ctx: ProjectContext) -> None:
        self.ctx = ctx
        self._observer: Observer | None = None
        self._handler: VaultWatcherHandler | None = None

    @classmethod
    def get(cls, ctx: ProjectContext) -> VaultWatcher:
        pid = ctx.project_id
        if pid not in cls._instances:
            cls._instances[pid] = VaultWatcher(ctx)
        return cls._instances[pid]

    def start(self, on_event: Callable[[str, str], None] | None = None) -> None:
        if self._observer is not None:
            return
        config = self.ctx.config
        if not config or not config.watcher_enabled or not config.vault_real_path:
            return
        self._handler = VaultWatcherHandler(self.ctx, on_event=on_event)
        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            self.ctx.config.vault_real_path,
            recursive=True,
        )
        self._observer.start()

    def stop(self) -> None:
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None

    @property
    def active(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
