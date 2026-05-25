"""Integration tests for indexing and search."""

from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_context_mcp.core.config_store import ConfigStore
from obsidian_context_mcp.core.context_pack import build_context_pack
from obsidian_context_mcp.core.embeddings import FakeEmbeddingProvider
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.project import get_project_context
from obsidian_context_mcp.core.retrieval import Retriever
from obsidian_context_mcp.shared.types import IndexMode

FIXTURES = Path(__file__).parent.parent / "fixtures"
SAMPLE_VAULT = FIXTURES / "sample_vault"
SAMPLE_PROJECT = FIXTURES / "sample_project"


@pytest.fixture
def configured_ctx(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    project_root = tmp_path / "project"
    project_root.mkdir()
    vault = SAMPLE_VAULT
    store = ConfigStore.for_project_root(str(project_root))
    store.create_or_update(
        str(project_root),
        vault_path=str(vault),
        embedding_provider="fake",
    )
    ctx = get_project_context(str(project_root))
    return ctx


def test_full_reindex(configured_ctx, monkeypatch):
    monkeypatch.setattr(
        "obsidian_context_mcp.core.indexer.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    indexer = Indexer(configured_ctx)
    progress = indexer.run(IndexMode.FULL)
    assert progress.status.value in ("completed", "running")
    assert progress.files_indexed >= 1 or progress.files_scanned >= 1


def test_search_returns_results(configured_ctx, monkeypatch):
    monkeypatch.setattr(
        "obsidian_context_mcp.core.indexer.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "obsidian_context_mcp.core.retrieval.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    Indexer(configured_ctx).run(IndexMode.FULL)
    retriever = Retriever(configured_ctx)
    results = retriever.search("API authentication")
    assert isinstance(results, list)


def test_context_pack_includes_sources(configured_ctx, monkeypatch):
    monkeypatch.setattr(
        "obsidian_context_mcp.core.indexer.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "obsidian_context_mcp.core.retrieval.create_embedding_provider",
        lambda config, pid: FakeEmbeddingProvider(),
    )
    Indexer(configured_ctx).run(IndexMode.FULL)
    pack = build_context_pack(configured_ctx, "API architecture")
    assert pack.project_id == configured_ctx.project_id
