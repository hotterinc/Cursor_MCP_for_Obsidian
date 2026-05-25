"""Global and per-project configuration storage."""

from __future__ import annotations

import contextlib
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from obsidian_context_mcp.core.app_paths import (
    compute_project_id,
    ensure_project_dirs,
    get_global_config_path,
    get_project_config_path,
)
from obsidian_context_mcp.core.errors import NotConfiguredError, ProjectNotFoundError
from obsidian_context_mcp.shared.constants import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_EMBEDDING_PROVIDER,
    DEFAULT_EXCLUDE,
    DEFAULT_INCLUDE,
    PROJECT_CONFIG_VERSION,
)
from obsidian_context_mcp.shared.types import ProjectConfig


def _atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            os.unlink(tmp)
        raise


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class GlobalConfigStore:
    def load(self) -> dict:
        return _load_json(get_global_config_path())

    def save(self, data: dict) -> None:
        _atomic_write_json(get_global_config_path(), data)

    def get_last_active_project_root(self) -> str | None:
        cfg = self.load()
        return cfg.get("lastActiveProjectRoot")

    def set_last_active_project_root(self, project_root: str) -> None:
        cfg = self.load()
        cfg["lastActiveProjectRoot"] = os.path.realpath(project_root)
        self.save(cfg)


class ConfigStore:
    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        ensure_project_dirs(project_id)

    @property
    def config_path(self) -> Path:
        return get_project_config_path(self.project_id)

    def load(self) -> ProjectConfig | None:
        if not self.config_path.exists():
            return None
        data = _load_json(self.config_path)
        return ProjectConfig.model_validate(data)

    def save(self, config: ProjectConfig) -> None:
        config.updated_at = datetime.utcnow().isoformat() + "Z"
        _atomic_write_json(self.config_path, config.model_dump())

    def create_or_update(
        self,
        project_root: str,
        *,
        vault_path: str | None = None,
        write_access: bool | None = None,
        backup_before_edit: bool | None = None,
        include: list[str] | None = None,
        exclude: list[str] | None = None,
        embedding_provider: str | None = None,
        embedding_model: str | None = None,
        watcher_enabled: bool | None = None,
        docs_subfolder: str | None = None,
    ) -> ProjectConfig:
        real_root = os.path.realpath(project_root)
        existing = self.load()
        if existing is None:
            config = ProjectConfig(
                version=PROJECT_CONFIG_VERSION,
                project_root=str(Path(project_root).resolve()),
                project_real_path=real_root,
                project_name=Path(real_root).name,
                include=include or list(DEFAULT_INCLUDE),
                exclude=exclude or list(DEFAULT_EXCLUDE),
                embedding_provider=embedding_provider or DEFAULT_EMBEDDING_PROVIDER,
                embedding_model=embedding_model or DEFAULT_EMBEDDING_MODEL,
            )
        else:
            config = existing

        if vault_path is not None:
            config.vault_path = str(Path(vault_path).resolve())
            config.vault_real_path = os.path.realpath(vault_path)
        if write_access is not None:
            config.write_access = write_access
        if backup_before_edit is not None:
            config.backup_before_edit = backup_before_edit
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
        if docs_subfolder is not None:
            config.docs_subfolder = docs_subfolder

        self.save(config)
        GlobalConfigStore().set_last_active_project_root(real_root)
        return config

    def require(self) -> ProjectConfig:
        config = self.load()
        if config is None:
            raise ProjectNotFoundError(f"No configuration for project {self.project_id}")
        return config

    def require_configured(self) -> ProjectConfig:
        config = self.require()
        if not config.configured:
            raise NotConfiguredError("Vault path is not configured for this project")
        return config

    @staticmethod
    def for_project_root(project_root: str) -> ConfigStore:
        project_id = compute_project_id(project_root)
        return ConfigStore(project_id)
