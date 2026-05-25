"""Vault validation and scanning."""

from __future__ import annotations

import fnmatch
import os
from dataclasses import dataclass, field
from pathlib import Path

from obsidian_context_mcp.core.errors import VaultValidationError


@dataclass
class VaultValidationResult:
    vault_path: str
    real_path: str
    markdown_files_count: int = 0
    warnings: list[str] = field(default_factory=list)
    can_read: bool = False
    can_write: bool = False


def _matches_any(path: str, patterns: list[str]) -> bool:
    norm = path.replace("\\", "/")
    for pattern in patterns:
        if fnmatch.fnmatch(norm, pattern):
            return True
        if fnmatch.fnmatch(norm, pattern.lstrip("**/")):
            return True
        if "**" in pattern and pattern.endswith("*.md") and norm.lower().endswith(".md"):
            return True
    return False


def scan_markdown_files(
    vault_root: Path,
    *,
    include: list[str],
    exclude: list[str],
    docs_subfolder: str | None = None,
) -> list[str]:
    base = vault_root
    if docs_subfolder:
        base = vault_root / docs_subfolder
    if not base.exists():
        return []

    results: list[str] = []
    for root, dirs, files in os.walk(base):
        rel_root = Path(root).relative_to(vault_root).as_posix()
        if rel_root != ".":
            if _matches_any(f"{rel_root}/", [e for e in exclude if e.endswith("/")]):
                dirs.clear()
                continue

        dirs[:] = [
            d
            for d in dirs
            if not d.startswith(".") or d not in {".obsidian", ".git", ".trash"}
        ]

        for fname in files:
            if not fname.lower().endswith(".md"):
                continue
            rel = (Path(rel_root) / fname).as_posix()
            if rel.startswith("./"):
                rel = rel[2:]
            if _matches_any(rel, exclude):
                continue
            if include and not _matches_any(rel, include):
                continue
            results.append(rel)

    return sorted(results)


def validate_vault_path(
    vault_path: str,
    *,
    include: list[str] | None = None,
    exclude: list[str] | None = None,
    docs_subfolder: str | None = None,
) -> VaultValidationResult:
    path = Path(vault_path)
    if not path.exists():
        raise VaultValidationError(f"Vault path does not exist: {vault_path}")
    if not path.is_dir():
        raise VaultValidationError(f"Vault path is not a directory: {vault_path}")

    real = os.path.realpath(vault_path)
    include = include or ["**/*.md"]
    exclude = exclude or [
        ".obsidian/**",
        ".git/**",
        "node_modules/**",
        ".trash/**",
        "templates/**",
    ]

    warnings: list[str] = []
    can_read = os.access(real, os.R_OK)
    can_write = os.access(real, os.W_OK)

    if not can_read:
        warnings.append("Vault directory is not readable")

    md_files = scan_markdown_files(Path(real), include=include, exclude=exclude, docs_subfolder=docs_subfolder)
    if len(md_files) == 0:
        warnings.append("No markdown files found matching include/exclude patterns")

    if (Path(real) / ".obsidian").exists():
        warnings.append(".obsidian folder detected — it will be excluded from indexing and writes")

    return VaultValidationResult(
        vault_path=str(path.resolve()),
        real_path=real,
        markdown_files_count=len(md_files),
        warnings=warnings,
        can_read=can_read,
        can_write=can_write,
    )
