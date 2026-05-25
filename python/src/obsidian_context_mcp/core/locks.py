"""File-based project locks."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager, suppress

from obsidian_context_mcp.core.app_paths import get_project_locks_dir, get_runtime_dir
from obsidian_context_mcp.core.errors import LockError


class ProjectLock:
    def __init__(self, project_id: str, name: str = "index", timeout: float = 0) -> None:
        self._lock_path = get_project_locks_dir(project_id) / f"{name}.lock"
        self._timeout = timeout
        self._fd: int | None = None

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout if self._timeout > 0 else None
        while True:
            try:
                self._lock_path.parent.mkdir(parents=True, exist_ok=True)
                self._fd = os.open(
                    self._lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(self._fd, str(os.getpid()).encode())
                return
            except FileExistsError:
                if deadline is not None and time.monotonic() >= deadline:
                    raise LockError(f"Could not acquire lock: {self._lock_path}")
                time.sleep(0.1)

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        with suppress(OSError):
            self._lock_path.unlink(missing_ok=True)

    def __enter__(self) -> ProjectLock:
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()


@contextmanager
def project_lock(project_id: str, name: str = "index", timeout: float = 30):
    lock = ProjectLock(project_id, name, timeout=timeout)
    lock.acquire()
    try:
        yield lock
    finally:
        lock.release()


class RuntimeLock:
    """Cross-process lock under app runtime dir (MCP + GUI sidecar)."""

    def __init__(self, name: str, timeout: float = 0) -> None:
        self._lock_path = get_runtime_dir() / f"{name}.lock"
        self._timeout = timeout
        self._fd: int | None = None

    def acquire(self) -> None:
        deadline = time.monotonic() + self._timeout if self._timeout > 0 else None
        while True:
            try:
                self._lock_path.parent.mkdir(parents=True, exist_ok=True)
                self._fd = os.open(
                    self._lock_path,
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                os.write(self._fd, str(os.getpid()).encode())
                return
            except FileExistsError:
                if deadline is not None and time.monotonic() >= deadline:
                    raise LockError(f"Could not acquire lock: {self._lock_path}")
                time.sleep(0.1)

    def release(self) -> None:
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
        with suppress(OSError):
            self._lock_path.unlink(missing_ok=True)

    def __enter__(self) -> RuntimeLock:
        self.acquire()
        return self

    def __exit__(self, *args: object) -> None:
        self.release()
