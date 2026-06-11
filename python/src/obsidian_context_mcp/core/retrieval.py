"""Hybrid retrieval: semantic + lexical."""

from __future__ import annotations

import json
from typing import Any, Union

from obsidian_context_mcp.core.embeddings import create_embedding_provider
from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.core.scope_filter import path_in_scope
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.core.vault_paths import get_vault_chroma_path
from obsidian_context_mcp.core.vector_store import create_vector_store, create_vector_store_at
from obsidian_context_mcp.core.work_context import WorkContext
from obsidian_context_mcp.shared.types import SearchMode, SearchResult

ContextLike = Union[ProjectContext, VaultContext, WorkContext]


def _normalize_ctx(ctx: ContextLike) -> WorkContext:
    if isinstance(ctx, WorkContext):
        return ctx
    if isinstance(ctx, VaultContext):
        return ctx.work_context()
    return WorkContext.from_project(ctx)


class Retriever:
    def __init__(self, ctx: ContextLike) -> None:
        self.work = _normalize_ctx(ctx)
        self.db = SQLiteStore(self.work.db_path)
        self.db.initialize()
        if isinstance(ctx, VaultContext):
            self.vector_store = create_vector_store_at(
                get_vault_chroma_path(ctx.data_dir),
                self.work.context_id,
            )
        else:
            self.vector_store = create_vector_store(self.work.context_id)
        self.embedder = create_embedding_provider(
            self.work.as_project_config(),
            self.work.context_id,
        )

    def _in_scope(self, relative_path: str) -> bool:
        if self.work.scope is None:
            return True
        return path_in_scope(relative_path, self.work.scope)

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        mode: SearchMode = SearchMode.HYBRID,
        filters: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        semantic: list[dict] = []
        lexical: list[dict] = []

        fetch_k = top_k * 4 if self.work.scope else top_k * 2

        if mode in (SearchMode.HYBRID, SearchMode.SEMANTIC):
            vector = self.embedder.embed_texts([query], is_query=True)[0]
            semantic = self.vector_store.search(
                self.work.context_id, vector, fetch_k, filters
            )

        if mode in (SearchMode.HYBRID, SearchMode.LEXICAL):
            lexical = self.db.fts_search(query, limit=fetch_k)

        merged: dict[str, float] = {}
        for item in semantic:
            cid = item["chunk_id"]
            merged[cid] = merged.get(cid, 0) + item["score"] * 0.6
        for item in lexical:
            cid = item["chunk_id"]
            lex_score = 1.0 / (1.0 + abs(item.get("score", 0)))
            merged[cid] = merged.get(cid, 0) + lex_score * 0.4

        results: list[SearchResult] = []
        for cid, score in sorted(merged.items(), key=lambda x: x[1], reverse=True):
            row = self.db.get_chunk_with_file(cid)
            if not row:
                continue
            rel_path = row["relative_path"]
            if not self._in_scope(rel_path):
                continue
            heading_path = json.loads(row.get("heading_path_json") or "[]")
            tags = json.loads(row.get("tags_json") or "[]")
            links = json.loads(row.get("links_json") or "[]")
            q_lower = query.lower()
            if q_lower in (row.get("file_title") or "").lower():
                score += 0.3
            if any(q_lower in h.lower() for h in heading_path):
                score += 0.2
            if any(q_lower in t.lower() for t in tags):
                score += 0.15
            results.append(
                SearchResult(
                    chunk_id=cid,
                    relative_path=rel_path,
                    title=row.get("file_title") or rel_path,
                    heading_path=heading_path,
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    score=min(score, 1.0),
                    text=row["text"],
                    tags=tags,
                    links=links,
                )
            )
            if len(results) >= top_k:
                break
        return results
