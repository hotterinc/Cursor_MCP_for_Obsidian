"""Request-scoped credentials, revalidated for every tool invocation."""
from __future__ import annotations

import contextvars
from dataclasses import replace

from obsidian_context_mcp.core.errors import ScopeAccessDeniedError
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.shared.types import AccessScope

_current_vault_ctx: contextvars.ContextVar[tuple[VaultContext, str | None] | None] = contextvars.ContextVar('vault_ctx', default=None)


def set_vault_context(ctx: VaultContext, scope_token: str | None = None) -> contextvars.Token[tuple[VaultContext, str | None] | None]:
    return _current_vault_ctx.set((ctx, scope_token))


def reset_vault_context(token: contextvars.Token[tuple[VaultContext, str | None] | None]) -> None:
    _current_vault_ctx.reset(token)


def get_vault_context() -> VaultContext | None:
    current = _current_vault_ctx.get()
    if current is None:
        return None
    ctx, credential = current
    if credential is None:
        return ctx
    scope = resolve_scope_from_token(ctx, credential)
    if scope is None:
        raise ScopeAccessDeniedError('Scope token was revoked or deleted')
    return replace(ctx, scope=scope)


def require_vault_context() -> VaultContext:
    ctx = get_vault_context()
    if ctx is None:
        raise RuntimeError('Vault context is not set for this request')
    return ctx


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(' ', 1)
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    return parts[1].strip() or None


def resolve_scope_from_token(vault_ctx: VaultContext, token: str | None) -> AccessScope | None:
    return vault_ctx.scope_store.get_by_token(token) if token else None
