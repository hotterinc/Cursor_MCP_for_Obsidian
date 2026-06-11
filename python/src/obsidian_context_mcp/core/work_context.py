"""Unified working context for indexing, search, and editing."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.shared.types import AccessScope, ProjectConfig, VaultConfig


@dataclass
class WorkContext:
    context_id: str
    vault_path: str
    vault_real_path: str
    include: list[str]
    exclude: list[str]
    docs_subfolder: str | None
    write_access: bool
    backup_before_edit: bool
    embedding_provider: str
    embedding_model: str
    db_path: Path
    logs_dir: Path
    backups_dir: Path
    scope: AccessScope | None = None

    @classmethod
    def from_project(cls, ctx: ProjectContext) -> WorkContext:
        config = ctx.config_store.require_configured()
        base = ctx.config_store.config_path.parent
        return cls(
            context_id=ctx.project_id,
            vault_path=config.vault_path or "",
            vault_real_path=config.vault_real_path or "",
            include=config.include,
            exclude=config.exclude,
            docs_subfolder=config.docs_subfolder,
            write_access=config.write_access,
            backup_before_edit=config.backup_before_edit,
            embedding_provider=config.embedding_provider,
            embedding_model=config.embedding_model,
            db_path=base / "db.sqlite",
            logs_dir=base / "logs",
            backups_dir=base / "backups",
        )

    @classmethod
    def from_vault_config(
        cls,
        config: VaultConfig,
        *,
        data_dir: Path,
        scope: AccessScope | None = None,
    ) -> WorkContext:
        from obsidian_context_mcp.core.vault_paths import (
            get_vault_backups_dir,
            get_vault_db_path,
            get_vault_logs_dir,
        )

        write_access = scope.write_access if scope else False
        return cls(
            context_id=config.vault_id,
            vault_path=config.vault_path,
            vault_real_path=config.vault_real_path,
            include=config.include,
            exclude=config.exclude,
            docs_subfolder=None,
            write_access=write_access,
            backup_before_edit=True,
            embedding_provider=config.embedding_provider,
            embedding_model=config.embedding_model,
            db_path=get_vault_db_path(data_dir),
            logs_dir=get_vault_logs_dir(data_dir),
            backups_dir=get_vault_backups_dir(data_dir),
            scope=scope,
        )

    def as_project_config(self) -> ProjectConfig:
        """Adapter for legacy SecurityBoundary / embedding helpers."""
        return ProjectConfig(
            project_root=self.vault_path,
            project_real_path=self.vault_real_path,
            project_name=Path(self.vault_path).name,
            vault_path=self.vault_path,
            vault_real_path=self.vault_real_path,
            include=self.include,
            exclude=self.exclude,
            docs_subfolder=self.docs_subfolder,
            write_access=self.write_access,
            backup_before_edit=self.backup_before_edit,
            embedding_provider=self.embedding_provider,
            embedding_model=self.embedding_model,
        )
