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


def test_index_rejects_traversal_before_read(configured_ctx, tmp_path):
    from obsidian_context_mcp.core.errors import PathSecurityError
    outside = tmp_path / "outside.md"
    outside.write_text("secret", encoding="utf-8")
    indexer = Indexer(configured_ctx)
    with pytest.raises(PathSecurityError):
        indexer.index_file("../outside.md")
    assert indexer.db.get_all_files() == []


def test_failed_file_marks_job_failed(configured_ctx, monkeypatch):
    indexer = Indexer(configured_ctx)
    def fail(_):
        raise RuntimeError("embedding unavailable")
    monkeypatch.setattr(indexer, "_index_file_unlocked", fail)
    progress = indexer.run(IndexMode.FULL)
    assert progress.status.value == "failed"
    assert progress.files_failed > 0


def test_scoped_search_does_not_starve_visible_candidates(configured_ctx, monkeypatch):
    from dataclasses import replace

    from obsidian_context_mcp.core.work_context import WorkContext
    from obsidian_context_mcp.shared.types import AccessScope, SearchMode
    work = replace(WorkContext.from_project(configured_ctx), scope=AccessScope(
        id="scope", name="Scope", include=["Architecture/**"], token="t"))
    retriever = Retriever(work)
    rows = [{"chunk_id": str(i), "score": i} for i in range(20)]
    monkeypatch.setattr(retriever.db, "fts_search", lambda query, limit: rows[:limit])
    monkeypatch.setattr(retriever.db, "get_chunk_with_file", lambda cid: {
        "relative_path": "Architecture/API.md" if cid == "19" else "Hidden.md",
        "start_line": 1, "end_line": 1, "text": "api"})
    monkeypatch.setattr(retriever.db, "count_chunks", lambda: len(rows))
    results = retriever.search("api", top_k=1, mode=SearchMode.LEXICAL)
    assert [result.chunk_id for result in results] == ["19"]


def test_search_score_never_goes_below_zero(configured_ctx, monkeypatch):
    from obsidian_context_mcp.shared.types import SearchMode

    retriever = Retriever(configured_ctx)
    monkeypatch.setattr(retriever.embedder, "embed_texts", lambda texts, is_query: [[0.0]])
    monkeypatch.setattr(
        retriever.vector_store,
        "search",
        lambda project_id, vector, top_k, filters: [{"chunk_id": "low", "score": -0.2}],
    )
    monkeypatch.setattr(retriever.db, "get_chunk_with_file", lambda cid: {
        "relative_path": "Note.md", "file_title": "Note", "start_line": 1,
        "end_line": 1, "text": "different text", "heading_path_json": "[]",
        "tags_json": "[]", "links_json": "[]",
    })

    results = retriever.search("unrelated", mode=SearchMode.SEMANTIC)
    assert results[0].score == 0.0


def test_incremental_rechecks_boundary_before_unchanged_skip(configured_ctx, tmp_path, monkeypatch):
    import os
    import subprocess
    from dataclasses import replace

    from obsidian_context_mcp.core.work_context import WorkContext
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.md").write_text("secret", encoding="utf-8")
    link = vault / "link"
    if os.name == "nt":
        subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(outside)],
                       check=True, capture_output=True)
    else:
        link.symlink_to(outside, target_is_directory=True)
    work = replace(WorkContext.from_project(configured_ctx),
                   vault_path=str(vault), vault_real_path=str(vault))
    indexer = Indexer(work)
    stat = (outside / "secret.md").stat()
    monkeypatch.setattr(indexer.db, "get_all_files", lambda: [{
        "relative_path": "link/secret.md", "mtime_ms": int(stat.st_mtime * 1000),
        "size": stat.st_size, "id": "existing"}])
    monkeypatch.setattr("obsidian_context_mcp.core.indexer.scan_markdown_files",
                        lambda *args, **kwargs: ["link/secret.md"])
    progress = indexer.run(IndexMode.INCREMENTAL)
    assert progress.files_failed == 1
    assert progress.files_skipped == 0
    assert progress.status.value == "failed"
