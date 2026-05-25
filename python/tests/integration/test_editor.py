"""Editor integration tests."""

from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from obsidian_context_mcp.core.config_store import ConfigStore
from obsidian_context_mcp.core.editor import Editor
from obsidian_context_mcp.core.embeddings import FakeEmbeddingProvider
from obsidian_context_mcp.core.errors import HashMismatchError, PatchError
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.project import get_project_context
from obsidian_context_mcp.shared.types import IndexMode, PatchMode

FIXTURES = Path(__file__).parent.parent / "fixtures"
SAMPLE_VAULT = FIXTURES / "sample_vault"


@pytest.fixture
def editor_ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    project_root = tmp_path / "project"
    project_root.mkdir()
    vault = tmp_path / "vault"
    vault.mkdir()
    for f in SAMPLE_VAULT.rglob("*.md"):
        dest = vault / f.relative_to(SAMPLE_VAULT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(f.read_text(encoding="utf-8"), encoding="utf-8")

    store = ConfigStore.for_project_root(str(project_root))
    store.create_or_update(
        str(project_root),
        vault_path=str(vault),
        write_access=True,
        embedding_provider="fake",
    )
    ctx = get_project_context(str(project_root))
    monkeypatch.setattr(
        "obsidian_context_mcp.core.indexer.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    Indexer(ctx).run(IndexMode.FULL)
    return Editor(ctx)


def test_hash_mismatch_blocks_edit(editor_ctx):
    editor_ctx.read_note("Setup.md")
    with pytest.raises(HashMismatchError):
        editor_ctx.patch_note(
            "Setup.md",
            "wronghash",
            PatchMode.APPEND_SECTION,
            {"heading": "## Test", "content": "x"},
        )


def test_replace_exact_multiple_matches(editor_ctx):
    note = editor_ctx.read_note("Setup.md")
    with pytest.raises(PatchError):
        editor_ctx.patch_note(
            "Setup.md",
            note["sha256"],
            PatchMode.REPLACE_EXACT,
            {"oldText": "e", "newText": "x"},
        )


def test_append_section_updates_file(editor_ctx, tmp_path):
    note = editor_ctx.read_note("Setup.md")
    result = editor_ctx.patch_note(
        "Setup.md",
        note["sha256"],
        PatchMode.APPEND_SECTION,
        {"heading": "## New Section", "content": "Added content"},
        create_backup_flag=True,
    )
    assert result.new_sha256 != note["sha256"]
    assert result.backup_path is not None


def test_unified_diff_patch_updates_file(editor_ctx):
    note = editor_ctx.read_note("Setup.md")
    updated = note["content"].replace("## Prerequisites", "## Requirements")
    diff = "".join(
        difflib.unified_diff(
            note["content"].splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile="a/Setup.md",
            tofile="b/Setup.md",
        )
    )
    result = editor_ctx.patch_note(
        "Setup.md",
        note["sha256"],
        PatchMode.UNIFIED_DIFF,
        {"diff": diff},
    )
    assert result.new_sha256 != note["sha256"]
