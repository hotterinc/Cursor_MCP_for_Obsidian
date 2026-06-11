"""Domain errors for obsidian-context-mcp."""

from __future__ import annotations


class DomainError(Exception):
    code: str = "domain_error"

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class NotConfiguredError(DomainError):
    code = "not_configured"


class PathSecurityError(DomainError):
    code = "path_security"


class WriteAccessDeniedError(DomainError):
    code = "write_access_denied"


class ScopeAccessDeniedError(DomainError):
    code = "scope_access_denied"


class HashMismatchError(DomainError):
    code = "hash_mismatch"


class PatchError(DomainError):
    code = "patch_error"


class VaultValidationError(DomainError):
    code = "vault_validation"


class IndexError(DomainError):
    code = "index_error"


class ProjectNotFoundError(DomainError):
    code = "project_not_found"


class LockError(DomainError):
    code = "lock_error"
