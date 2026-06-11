"""Backup management before edits."""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from obsidian_context_mcp.core.app_paths import get_project_backups_dir


def encode_relative_path(relative_path: str) -> str:
    return quote(relative_path.replace("\\", "/"), safe="")


def create_backup(
    project_id: str,
    *,
    relative_path: str,
    source_path: Path,
    operation: str,
    old_sha256: str,
    new_sha256: str | None = None,
    backups_dir: Path | None = None,
) -> Path:
    now = datetime.utcnow()
    base = backups_dir or get_project_backups_dir(project_id)
    date_dir = base / now.strftime("%Y-%m-%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    ts = now.strftime("%H%M%S_%f")
    encoded = encode_relative_path(relative_path)
    backup_md = date_dir / f"{ts}__{encoded}.md"
    shutil.copy2(source_path, backup_md)
    meta = {
        "operation": operation,
        "relativePath": relative_path,
        "oldSha256": old_sha256,
        "newSha256": new_sha256,
        "createdAt": now.isoformat() + "Z",
    }
    backup_md.with_suffix(".md.meta.json").write_text(
        json.dumps(meta, indent=2), encoding="utf-8"
    )
    return backup_md
