"""Safe markdown editing with atomic writes."""

from __future__ import annotations

import difflib
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from obsidian_context_mcp.core.backups import create_backup
from obsidian_context_mcp.core.errors import HashMismatchError, PatchError
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.markdown_parser import (
    compute_sha256,
    parse_markdown_text,
    read_file_text,
)
from obsidian_context_mcp.core.project import ProjectContext, compute_file_id
from obsidian_context_mcp.core.security import SecurityBoundary
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.shared.types import PatchMode


@dataclass
class EditResult:
    relative_path: str
    old_sha256: str
    new_sha256: str
    backup_path: str | None
    dry_run: bool


class Editor:
    def __init__(self, ctx: ProjectContext) -> None:
        self.ctx = ctx
        self.config = ctx.config_store.require_configured()
        self.boundary = SecurityBoundary(self.config)
        self.db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
        self.db.initialize()

    def read_note(self, relative_path: str) -> dict[str, Any]:
        resolved = self.boundary.resolve_read_path(relative_path)
        path = Path(resolved.real_path)
        text, _ = read_file_text(path)
        note = parse_markdown_text(resolved.relative_path, text)
        return {
            "relative_path": resolved.relative_path,
            "sha256": note.sha256,
            "content": text,
            "frontmatter": note.frontmatter,
            "headings": [h.model_dump() for h in note.headings],
        }

    def _read_and_verify(self, relative_path: str, expected_sha256: str) -> tuple[Path, str, str]:
        resolved = self.boundary.resolve_write_path(relative_path)
        path = Path(resolved.real_path)
        text, eol = read_file_text(path)
        current_hash = compute_sha256(text)
        if current_hash != expected_sha256:
            raise HashMismatchError(
                f"Hash mismatch for {relative_path}",
                details={"expected": expected_sha256, "actual": current_hash},
            )
        return path, text, eol

    def _apply_patch(self, text: str, mode: PatchMode, patch: dict[str, Any]) -> str:
        if mode == PatchMode.REPLACE_EXACT:
            old = patch["oldText"]
            new = patch["newText"]
            idx = patch.get("occurrenceIndex")
            count = text.count(old)
            if count == 0:
                raise PatchError("oldText not found")
            if idx is None and count > 1:
                raise PatchError(f"oldText found {count} times; specify occurrenceIndex")
            if idx is not None:
                parts = text.split(old)
                if idx >= len(parts) - 1:
                    raise PatchError("occurrenceIndex out of range")
                return old.join(parts[: idx + 1]) + new + old.join(parts[idx + 1 :])
            return text.replace(old, new, 1)

        if mode == PatchMode.UNIFIED_DIFF:
            diff = patch["diff"]
            text.splitlines(keepends=True)
            result = list(difflib.restore(diff.splitlines(), 2))
            if not result:
                raise PatchError("Failed to apply unified diff")
            return "".join(result)

        if mode == PatchMode.APPEND_SECTION:
            heading = patch["heading"]
            content = patch["content"]
            sep = "\n\n" if not text.endswith("\n") else "\n"
            return text.rstrip() + sep + heading + "\n\n" + content + "\n"

        if mode == PatchMode.UPSERT_SECTION:
            heading = patch["heading"]
            content = patch["content"]
            level = len(re.match(r"^(#+)", heading).group(1)) if re.match(r"^(#+)", heading) else 2
            pattern = re.compile(
                rf"^{re.escape(heading)}\s*$.*?(?=^#{{{1,{level}}}}\s|\Z)",
                re.MULTILINE | re.DOTALL,
            )
            section = heading + "\n\n" + content + "\n"
            if pattern.search(text):
                return pattern.sub(section, text)
            sep = "\n\n" if not text.endswith("\n") else "\n"
            return text.rstrip() + sep + section

        raise PatchError(f"Unknown patch mode: {mode}")

    def patch_note(
        self,
        relative_path: str,
        expected_sha256: str,
        mode: PatchMode,
        patch: dict[str, Any],
        *,
        dry_run: bool = False,
        create_backup_flag: bool = True,
    ) -> EditResult:
        path, text, eol = self._read_and_verify(relative_path, expected_sha256)
        new_text = self._apply_patch(text, mode, patch)
        new_hash = compute_sha256(new_text)
        backup_path = None

        if dry_run:
            return EditResult(relative_path, expected_sha256, new_hash, None, True)

        if create_backup_flag and self.config.backup_before_edit:
            backup_path = str(
                create_backup(
                    self.ctx.project_id,
                    relative_path=relative_path,
                    source_path=path,
                    operation="patch",
                    old_sha256=expected_sha256,
                    new_sha256=new_hash,
                )
            )

        self._atomic_write(path, new_text, eol)
        Indexer(self.ctx).index_file(relative_path)

        file_id = compute_file_id(
            self.ctx.project_id,
            self.config.vault_real_path or "",
            relative_path,
        )
        self.db.log_operation(
            str(uuid.uuid4()),
            "patch",
            file_id,
            relative_path,
            expected_sha256,
            new_hash,
            "completed",
        )
        return EditResult(relative_path, expected_sha256, new_hash, backup_path, False)

    def create_note(
        self,
        relative_path: str,
        content: str,
        *,
        overwrite: bool = False,
        create_backup_flag: bool = True,
    ) -> EditResult:
        resolved = self.boundary.resolve_write_path(relative_path)
        path = Path(resolved.real_path)
        if path.exists() and not overwrite:
            raise PatchError("File already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        eol = detect_eol(content)
        new_hash = compute_sha256(content)
        self._atomic_write(path, content, eol)
        Indexer(self.ctx).index_file(resolved.relative_path)
        return EditResult(resolved.relative_path, "", new_hash, None, False)

    def delete_note(
        self,
        relative_path: str,
        expected_sha256: str,
        *,
        create_backup_flag: bool = True,
    ) -> EditResult:
        path, text, _ = self._read_and_verify(relative_path, expected_sha256)
        backup_path = None
        if create_backup_flag and self.config.backup_before_edit:
            backup_path = str(
                create_backup(
                    self.ctx.project_id,
                    relative_path=relative_path,
                    source_path=path,
                    operation="delete",
                    old_sha256=expected_sha256,
                )
            )
        path.unlink(missing_ok=True)
        Indexer(self.ctx).index_file(relative_path)
        return EditResult(relative_path, expected_sha256, "", backup_path, False)

    def rename_note(
        self,
        from_relative_path: str,
        to_relative_path: str,
        expected_sha256: str,
        *,
        create_backup_flag: bool = True,
    ) -> EditResult:
        from_resolved = self.boundary.resolve_write_path(from_relative_path)
        to_resolved = self.boundary.resolve_write_path(to_relative_path)
        from_path = Path(from_resolved.real_path)
        to_path = Path(to_resolved.real_path)
        text, eol = read_file_text(from_path)
        current_hash = compute_sha256(text)
        if current_hash != expected_sha256:
            raise HashMismatchError("Hash mismatch", details={"expected": expected_sha256, "actual": current_hash})
        if to_path.exists():
            raise PatchError("Target path already exists")
        to_path.parent.mkdir(parents=True, exist_ok=True)
        from_path.rename(to_path)
        Indexer(self.ctx).index_file(from_relative_path)
        Indexer(self.ctx).index_file(to_resolved.relative_path)
        return EditResult(to_resolved.relative_path, expected_sha256, current_hash, None, False)

    @staticmethod
    def _atomic_write(path: Path, content: str, eol: str) -> None:
        normalized = content.replace("\r\n", "\n").replace("\n", eol)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8", newline="") as f:
            f.write(normalized)
            f.flush()
            os.fsync(f.fileno())
        tmp.replace(path)


def detect_eol(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    return "\n"
