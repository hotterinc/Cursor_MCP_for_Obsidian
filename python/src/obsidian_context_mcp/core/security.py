"""Strict path security boundary for vault access."""

from __future__ import annotations

import os
import sys
from pathlib import Path, PurePosixPath

from obsidian_context_mcp.core.errors import PathSecurityError, ScopeAccessDeniedError, WriteAccessDeniedError
from obsidian_context_mcp.core.scope_filter import path_in_scope
from obsidian_context_mcp.shared.constants import BLOCKED_WRITE_PREFIXES
from obsidian_context_mcp.shared.types import AccessScope, ProjectConfig, ResolvedPath


def _normalize_relative(relative_path: str) -> str:
    if "\x00" in relative_path:
        raise PathSecurityError("Path contains null bytes")
    rel = relative_path.replace("\\", "/").lstrip("/")
    if ".." in PurePosixPath(rel).parts:
        raise PathSecurityError("Path traversal is not allowed")
    return rel


def _is_inside_vault(vault_real: str, target_real: str) -> bool:
    vault = os.path.normcase(os.path.normpath(vault_real))
    target = os.path.normcase(os.path.normpath(target_real))
    if sys.platform == "win32":
        if vault == target:
            return True
        prefix = vault if vault.endswith(os.sep) else vault + os.sep
        return target.startswith(prefix)
    return target == vault or target.startswith(vault + os.sep)


def _is_blocked_write_path(relative_path: str) -> bool:
    norm = relative_path.replace("\\", "/").lstrip("/")
    for prefix in BLOCKED_WRITE_PREFIXES:
        if norm == prefix.rstrip("/") or norm.startswith(prefix):
            return True
    return False


class SecurityBoundary:
    def __init__(self, config: ProjectConfig) -> None:
        if not config.vault_real_path:
            raise PathSecurityError("Vault is not configured")
        self._vault_path = Path(config.vault_path or config.vault_real_path)
        self._vault_real = os.path.realpath(config.vault_real_path)
        self._write_access = config.write_access
        self._docs_subfolder = config.docs_subfolder

    @property
    def vault_real_path(self) -> str:
        return self._vault_real

    def assert_inside_vault(self, real_path: str) -> None:
        resolved = os.path.realpath(real_path)
        if not _is_inside_vault(self._vault_real, resolved):
            raise PathSecurityError(f"Path escapes vault boundary: {real_path}")

    def _resolve(self, relative_path: str, *, for_write: bool) -> ResolvedPath:
        rel = _normalize_relative(relative_path)
        if not rel.lower().endswith(".md"):
            raise PathSecurityError("Only .md files are allowed")

        if for_write:
            if not self._write_access:
                raise WriteAccessDeniedError("Write access is disabled")
            if _is_blocked_write_path(rel):
                raise PathSecurityError(f"Writes to '{rel}' are blocked")

        base = self._vault_path
        if self._docs_subfolder:
            base = base / self._docs_subfolder

        absolute = (base / rel).resolve()
        real = os.path.realpath(absolute)
        self.assert_inside_vault(real)

        # Recompute relative from vault root
        vault_base = Path(self._vault_real)
        try:
            final_rel = str(Path(real).relative_to(vault_base)).replace("\\", "/")
        except ValueError as exc:
            raise PathSecurityError("Resolved path is outside vault") from exc

        return ResolvedPath(
            relative_path=final_rel,
            absolute_path=str(absolute),
            real_path=real,
        )

    def resolve_read_path(self, relative_path: str) -> ResolvedPath:
        return self._resolve(relative_path, for_write=False)

    def resolve_write_path(self, relative_path: str) -> ResolvedPath:
        return self._resolve(relative_path, for_write=True)

    def resolve_vault_root(self) -> str:
        return self._vault_real


class ScopeBoundary:
    """Enforces access scope folder restrictions on top of vault security."""

    def __init__(self, boundary: SecurityBoundary, scope: AccessScope | None) -> None:
        self._boundary = boundary
        self._scope = scope

    def assert_in_scope(self, relative_path: str) -> None:
        if self._scope is None:
            return
        if not path_in_scope(relative_path, self._scope):
            raise ScopeAccessDeniedError(
                f"Path '{relative_path}' is outside the allowed scope '{self._scope.name}'"
            )

    def resolve_read_path(self, relative_path: str) -> ResolvedPath:
        resolved = self._boundary.resolve_read_path(relative_path)
        self.assert_in_scope(resolved.relative_path)
        return resolved

    def resolve_write_path(self, relative_path: str) -> ResolvedPath:
        resolved = self._boundary.resolve_write_path(relative_path)
        self.assert_in_scope(resolved.relative_path)
        return resolved

    def resolve_vault_root(self) -> str:
        return self._boundary.resolve_vault_root()
