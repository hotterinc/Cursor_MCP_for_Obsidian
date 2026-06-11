"""Request-scoped auth context for vault MCP."""

from __future__ import annotations

import contextvars

from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.shared.types import AccessScope

_current_vault_ctx: contextvars.ContextVar[VaultContext | None] = contextvars.ContextVar(
    "vault_ctx", default=None
)


def set_vault_context(ctx: VaultContext) -> contextvars.Token:
    return _current_vault_ctx.set(ctx)


def reset_vault_context(token: contextvars.Token) -> None:
    _current_vault_ctx.reset(token)


def get_vault_context() -> VaultContext | None:
    return _current_vault_ctx.get()


def require_vault_context() -> VaultContext:
    ctx = get_vault_context()
    if ctx is None:
        raise RuntimeError("Vault context is not set for this request")
    return ctx


def parse_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def resolve_scope_from_token(vault_ctx: VaultContext, token: str | None) -> AccessScope | None:
    if token is None:
        return None
    return vault_ctx.scope_store.get_by_token(token)
