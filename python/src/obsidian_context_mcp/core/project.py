"""Project detection and context."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path

from obsidian_context_mcp.core.app_paths import compute_project_id, get_project_logs_dir
from obsidian_context_mcp.core.config_store import ConfigStore, GlobalConfigStore
from obsidian_context_mcp.core.logging import setup_logging
from obsidian_context_mcp.shared.constants import ENV_PROJECT_ROOT
from obsidian_context_mcp.shared.types import IndexStatus, ProjectConfig


@dataclass
class ProjectContext:
    project_id: str
    project_root: str
    project_real_path: str
    project_name: str
    config: ProjectConfig | None
    config_store: ConfigStore

    @property
    def configured(self) -> bool:
        return self.config is not None and self.config.configured

    def get_status(self) -> IndexStatus:
        if self.config is None or not self.config.configured:
            return IndexStatus.NOT_CONFIGURED
        return IndexStatus.READY


def resolve_project_root(
    *,
    cli_root: str | None = None,
    env_root: str | None = None,
    mcp_workspace_roots: list[str] | None = None,
    cwd: str | None = None,
    use_last_active: bool = True,
) -> str | None:
    if cli_root:
        return os.path.realpath(cli_root)
    if env_root:
        return os.path.realpath(env_root)
    if mcp_workspace_roots:
        for root in mcp_workspace_roots:
            if root and Path(root).exists():
                return os.path.realpath(root)
    if cwd:
        return os.path.realpath(cwd)
    if use_last_active:
        last = GlobalConfigStore().get_last_active_project_root()
        if last and Path(last).exists():
            return last
    return None


def get_project_context(project_root: str) -> ProjectContext:
    real = os.path.realpath(project_root)
    project_id = compute_project_id(real)
    store = ConfigStore(project_id)
    config = store.load()
    setup_logging(log_file=get_project_logs_dir(project_id) / "core.log")
    return ProjectContext(
        project_id=project_id,
        project_root=str(Path(project_root).resolve()),
        project_real_path=real,
        project_name=Path(real).name,
        config=config,
        config_store=store,
    )


def detect_project_context(
    *,
    cli_root: str | None = None,
    mcp_workspace_roots: list[str] | None = None,
) -> ProjectContext | None:
    env_root = os.environ.get(ENV_PROJECT_ROOT)
    cwd = os.getcwd()
    root = resolve_project_root(
        cli_root=cli_root,
        env_root=env_root,
        mcp_workspace_roots=mcp_workspace_roots,
        cwd=cwd,
    )
    if root is None:
        return None
    return get_project_context(root)


def compute_file_id(project_id: str, vault_real_path: str, relative_path: str) -> str:
    key = f"{project_id}:{vault_real_path}:{relative_path}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def compute_chunk_id(file_id: str, chunk_index: int, chunk_hash: str) -> str:
    key = f"{file_id}:{chunk_index}:{chunk_hash}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
