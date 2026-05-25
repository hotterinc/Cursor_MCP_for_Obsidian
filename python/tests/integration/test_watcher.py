"""Watcher integration test."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from obsidian_context_mcp.core.config_store import ConfigStore
from obsidian_context_mcp.core.embeddings import FakeEmbeddingProvider
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.project import get_project_context
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.watcher import VaultWatcher
from obsidian_context_mcp.shared.types import IndexMode

FIXTURES = Path(__file__).parent.parent / "fixtures"
SAMPLE_VAULT = FIXTURES / "sample_vault"


@pytest.fixture
def watcher_ctx(tmp_path, monkeypatch):
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
    store.create_or_update(str(project_root), vault_path=str(vault), embedding_provider="fake")
    ctx = get_project_context(str(project_root))
    monkeypatch.setattr(
        "obsidian_context_mcp.core.indexer.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "obsidian_context_mcp.core.watcher.Indexer",
        lambda c: Indexer(c),
    )
    Indexer(ctx).run(IndexMode.FULL)
    return ctx, vault


def test_watcher_detects_external_change(watcher_ctx):
    ctx, vault = watcher_ctx
    watcher = VaultWatcher.get(ctx)
    watcher.start()
    assert watcher.active

    note = vault / "watched.md"
    note.write_text("# Watched\n\nContent\n", encoding="utf-8")
    time.sleep(2)

    db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
    row = db.get_file_by_path("watched.md")
    watcher.stop()
    assert row is not None
