"""Access scope storage and token management."""

from __future__ import annotations

import secrets
from pathlib import Path

from obsidian_context_mcp.core.config_store import _atomic_write_json, _load_json
from obsidian_context_mcp.core.vault_paths import ensure_vault_data_dirs, get_scopes_path
from obsidian_context_mcp.shared.constants import SCOPE_TOKEN_PREFIX
from obsidian_context_mcp.shared.types import AccessScope, ScopesFile


def generate_scope_token() -> str:
    return f"{SCOPE_TOKEN_PREFIX}{secrets.token_urlsafe(24)}"


class ScopeStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        ensure_vault_data_dirs(data_dir)

    @property
    def scopes_path(self) -> Path:
        return get_scopes_path(self.data_dir)

    def load(self) -> ScopesFile:
        if not self.scopes_path.exists():
            return ScopesFile()
        return ScopesFile.model_validate(_load_json(self.scopes_path))

    def save(self, data: ScopesFile) -> None:
        _atomic_write_json(self.scopes_path, data.model_dump())

    def list_scopes(self) -> list[AccessScope]:
        return self.load().scopes

    def get_by_id(self, scope_id: str) -> AccessScope | None:
        for scope in self.load().scopes:
            if scope.id == scope_id:
                return scope
        return None

    def get_by_token(self, token: str) -> AccessScope | None:
        if not token:
            return None
        for scope in self.load().scopes:
            if scope.token == token:
                return scope
        return None

    def upsert(self, scope: AccessScope) -> AccessScope:
        data = self.load()
        if not scope.token:
            scope.token = generate_scope_token()
        updated: list[AccessScope] = []
        found = False
        for existing in data.scopes:
            if existing.id == scope.id:
                updated.append(scope)
                found = True
            else:
                updated.append(existing)
        if not found:
            updated.append(scope)
        data.scopes = updated
        self.save(data)
        return scope

    def delete(self, scope_id: str) -> bool:
        data = self.load()
        before = len(data.scopes)
        data.scopes = [s for s in data.scopes if s.id != scope_id]
        if len(data.scopes) == before:
            return False
        self.save(data)
        return True

    def regenerate_token(self, scope_id: str) -> AccessScope | None:
        scope = self.get_by_id(scope_id)
        if scope is None:
            return None
        scope.token = generate_scope_token()
        return self.upsert(scope)
