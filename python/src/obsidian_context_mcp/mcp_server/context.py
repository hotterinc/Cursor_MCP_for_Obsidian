from __future__ import annotations

from contextvars import ContextVar

project_root_override: ContextVar[str | None] = ContextVar("project_root_override", default=None)
