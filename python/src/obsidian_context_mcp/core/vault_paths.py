"""Vault-centric data paths (Obsidian plugin data directory)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from obsidian_context_mcp.shared.constants import PLUGIN_ID


def compute_vault_id(vault_path: str | Path) -> str:
    real = os.path.realpath(str(vault_path))
    return hashlib.sha256(real.encode("utf-8")).hexdigest()


def default_plugin_data_dir(vault_path: str | Path) -> Path:
    """Default data dir: `<vault>/.obsidian/plugins/obsidian-context-mcp/data`."""
    vault = Path(vault_path).resolve()
    return vault / ".obsidian" / "plugins" / PLUGIN_ID / "data"


def ensure_vault_data_dirs(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "index").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "backups").mkdir(parents=True, exist_ok=True)
    (data_dir / "locks").mkdir(parents=True, exist_ok=True)


def get_vault_config_path(data_dir: Path) -> Path:
    return data_dir / "vault.json"


def get_scopes_path(data_dir: Path) -> Path:
    return data_dir / "scopes.json"


def get_runtime_path(data_dir: Path) -> Path:
    return data_dir / "runtime.json"


def get_vault_db_path(data_dir: Path) -> Path:
    return data_dir / "index" / "db.sqlite"


def get_vault_chroma_path(data_dir: Path) -> Path:
    path = data_dir / "index" / "chroma"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_logs_dir(data_dir: Path) -> Path:
    path = data_dir / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_backups_dir(data_dir: Path) -> Path:
    path = data_dir / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_locks_dir(data_dir: Path) -> Path:
    path = data_dir / "locks"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_models_cache_dir(data_dir: Path) -> Path:
    """Embedding models cache — kept inside plugin data dir (self-contained vault)."""
    path = data_dir / "models-cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_vault_llm_models_dir(data_dir: Path) -> Path:
    """Downloaded GGUF chat models for built-in LLM."""
    path = data_dir / "models-llm"
    path.mkdir(parents=True, exist_ok=True)
    return path
