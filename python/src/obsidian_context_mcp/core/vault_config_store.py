"""Vault configuration stored in Obsidian plugin data directory."""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from obsidian_context_mcp.core.config_store import _atomic_write_json, _load_json
from obsidian_context_mcp.core.vault_paths import (
    compute_vault_id,
    ensure_vault_data_dirs,
    get_vault_config_path,
)
from obsidian_context_mcp.shared.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    VAULT_CONFIG_VERSION,
)
from obsidian_context_mcp.shared.types import VaultConfig


class VaultConfigStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir
        ensure_vault_data_dirs(data_dir)

    @property
    def config_path(self) -> Path:
        return get_vault_config_path(self.data_dir)

    def load(self) -> VaultConfig | None:
        if not self.config_path.exists():
            return None
        return VaultConfig.model_validate(_load_json(self.config_path))

    def save(self, config: VaultConfig) -> None:
        config.updated_at = datetime.utcnow().isoformat() + "Z"
        _atomic_write_json(self.config_path, config.model_dump())

    def create_or_update(
        self,
        vault_path: str,
        *,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        watcher_enabled: bool | None = None,
    ) -> VaultConfig:
        real = os.path.realpath(vault_path)
        vault_id = compute_vault_id(real)
        existing = self.load()
        if existing is None:
            config = VaultConfig(
                version=VAULT_CONFIG_VERSION,
                vault_id=vault_id,
                vault_path=str(Path(vault_path).resolve()),
                vault_real_path=real,
                include=include or list(DEFAULT_INCLUDE),
                exclude=exclude or list(DEFAULT_EXCLUDE),
                embedding_provider=embedding_provider or DEFAULT_EMBEDDING_PROVIDER,
                embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
            )
        else:
            config = existing
            config.vault_path = str(Path(vault_path).resolve())
            config.vault_real_path = real
            config.vault_id = vault_id

        if include is not None:
            config.include = include
        if exclude is not None:
            config.exclude = exclude
        if embedding_provider is not None:
            config.embedding_provider = embedding_provider
        if embedding_model is not None:
            config.embedding_model = embedding_model
        if watcher_enabled is not None:
            config.watcher_enabled = watcher_enabled

        self.save(config)
        return config

    def require(self) -> VaultConfig:
        config = self.load()
        if config is None:
            raise FileNotFoundError(f"No vault config at {self.config_path}")
        return config
