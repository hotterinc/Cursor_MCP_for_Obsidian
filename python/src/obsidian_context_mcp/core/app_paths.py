"""Application data paths via platformdirs."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

import platformdirs

from obsidian_context_mcp.shared.constants import APP_NAME, ENV_DATA_DIR


def _is_windows_store_sandbox(path: Path) -> bool:
    parts = {p.lower() for p in path.parts}
    return "packages" in parts and "localcache" in parts


def _canonical_app_data_dir() -> Path:
    if os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            return Path(local) / APP_NAME / APP_NAME
    if os.name == "posix" and (Path.home() / "Library").exists():
        return Path.home() / "Library" / "Application Support" / APP_NAME
    return Path.home() / ".local" / "share" / APP_NAME


def get_app_data_dir() -> Path:
    override = os.environ.get(ENV_DATA_DIR)
    if override:
        path = Path(override)
    else:
        platform_path = Path(platformdirs.user_data_dir(APP_NAME))
        path = _canonical_app_data_dir() if _is_windows_store_sandbox(platform_path) else platform_path
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_global_config_path() -> Path:
    return get_app_data_dir() / "config.json"


def get_runtime_dir() -> Path:
    path = get_app_data_dir() / "runtime"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_desktop_lock_path() -> Path:
    return get_runtime_dir() / "desktop.lock"


def get_open_request_path() -> Path:
    return get_runtime_dir() / "open-request.json"


def compute_project_id(project_root: str | Path) -> str:
    real = os.path.realpath(str(project_root))
    return hashlib.sha256(real.encode("utf-8")).hexdigest()


def get_project_dir(project_id: str) -> Path:
    path = get_app_data_dir() / "projects" / project_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_config_path(project_id: str) -> Path:
    return get_project_dir(project_id) / "project.json"


def get_project_db_path(project_id: str) -> Path:
    return get_project_dir(project_id) / "db.sqlite"


def get_project_chroma_path(project_id: str) -> Path:
    path = get_project_dir(project_id) / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_backups_dir(project_id: str) -> Path:
    path = get_project_dir(project_id) / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_logs_dir(project_id: str) -> Path:
    path = get_project_dir(project_id) / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_cache_dir(project_id: str) -> Path:
    path = get_project_dir(project_id) / "cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_locks_dir(project_id: str) -> Path:
    path = get_project_dir(project_id) / "locks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_shared_models_cache_dir() -> Path:
    """Single HF cache for all projects (avoids per-project re-download and lock fights)."""
    path = get_app_data_dir() / "models-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_project_models_dir(project_id: str) -> Path:
    path = get_project_dir(project_id) / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_project_dirs(project_id: str) -> None:
    get_project_dir(project_id)
    get_project_chroma_path(project_id)
    get_project_backups_dir(project_id)
    get_project_logs_dir(project_id)
    get_project_cache_dir(project_id)
    get_project_locks_dir(project_id)
    get_project_models_dir(project_id)
