"""Path filtering for access scopes."""

from __future__ import annotations

from obsidian_context_mcp.core.vault import _matches_any
from obsidian_context_mcp.shared.types import AccessScope


def path_in_scope(relative_path: str, scope: AccessScope) -> bool:
    norm = relative_path.replace("\\", "/").lstrip("/")
    if scope.exclude and _matches_any(norm, scope.exclude):
        return False
    if scope.include:
        return _matches_any(norm, scope.include)
    return True


def filter_paths(paths: list[str], scope: AccessScope | None) -> list[str]:
    if scope is None:
        return paths
    return [p for p in paths if path_in_scope(p, scope)]
