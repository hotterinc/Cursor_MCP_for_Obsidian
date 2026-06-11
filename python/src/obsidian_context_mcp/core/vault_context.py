"""Vault-centric context for Obsidian-hosted MCP."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from obsidian_context_mcp.core.logging import setup_logging
from obsidian_context_mcp.core.scope_store import ScopeStore
from obsidian_context_mcp.core.vault_config_store import VaultConfigStore
from obsidian_context_mcp.core.vault_paths import (
    compute_vault_id,
    default_plugin_data_dir,
    ensure_vault_data_dirs,
    get_vault_logs_dir,
)
from obsidian_context_mcp.core.work_context import WorkContext
from obsidian_context_mcp.shared.types import AccessScope, IndexStatus, VaultConfig


@dataclass
class VaultContext:
    vault_id: str
    vault_path: str
    vault_real_path: str
    data_dir: Path
    config: VaultConfig
    config_store: VaultConfigStore
    scope_store: ScopeStore
    scope: AccessScope | None = None

    @property
    def configured(self) -> bool:
        return bool(self.config.vault_real_path)

    def get_status(self) -> IndexStatus:
        if not self.configured:
            return IndexStatus.NOT_CONFIGURED
        return IndexStatus.READY

    def work_context(self) -> WorkContext:
        return WorkContext.from_vault_config(
            self.config,
            data_dir=self.data_dir,
            scope=self.scope,
        )


def get_vault_context(
    vault_path: str,
    *,
    data_dir: Path | None = None,
    scope: AccessScope | None = None,
) -> VaultContext:
    real = os.path.realpath(vault_path)
    resolved_data = data_dir or default_plugin_data_dir(real)
    ensure_vault_data_dirs(resolved_data)
    config_store = VaultConfigStore(resolved_data)
    config = config_store.load()
    if config is None:
        config = config_store.create_or_update(real)
    setup_logging(log_file=get_vault_logs_dir(resolved_data) / "vault-server.log")
    return VaultContext(
        vault_id=compute_vault_id(real),
        vault_path=str(Path(vault_path).resolve()),
        vault_real_path=real,
        data_dir=resolved_data,
        config=config,
        config_store=config_store,
        scope_store=ScopeStore(resolved_data),
        scope=scope,
    )
