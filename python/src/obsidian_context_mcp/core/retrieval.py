"""Hybrid retrieval: semantic + lexical."""

from __future__ import annotations

import json
from typing import Any

from obsidian_context_mcp.core.embeddings import create_embedding_provider
from obsidian_context_mcp.core.project import ProjectContext
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vector_store import create_vector_store
from obsidian_context_mcp.shared.types import SearchMode, SearchResult


class Retriever:
    def __init__(self, ctx: ProjectContext) -> None:
        self.ctx = ctx
        self.config = ctx.config_store.require_configured()
        self.db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
        self.db.initialize()
        self.vector_store = create_vector_store(ctx.project_id)
        self.embedder = create_embedding_provider(self.config, ctx.project_id)

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

        if mode in (SearchMode.HYBRID, SearchMode.SEMANTIC):
            vector = self.embedder.embed_texts([query], is_query=True)[0]
            semantic = self.vector_store.search(self.ctx.project_id, vector, top_k * 2, filters)

        if mode in (SearchMode.HYBRID, SearchMode.LEXICAL):
            lexical = self.db.fts_search(query, limit=top_k * 2)

        merged: dict[str, float] = {}
        for item in semantic:
            cid = item["chunk_id"]
            merged[cid] = merged.get(cid, 0) + item["score"] * 0.6
        for item in lexical:
            cid = item["chunk_id"]
            # BM25 returns negative scores (lower is better)
            lex_score = 1.0 / (1.0 + abs(item.get("score", 0)))
            merged[cid] = merged.get(cid, 0) + lex_score * 0.4

        results: list[SearchResult] = []
        for cid, score in sorted(merged.items(), key=lambda x: x[1], reverse=True)[:top_k]:
            row = self.db.get_chunk_with_file(cid)
            if not row:
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
                    relative_path=row["relative_path"],
                    title=row.get("file_title") or row["relative_path"],
                    heading_path=heading_path,
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    score=min(score, 1.0),
                    text=row["text"],
                    tags=tags,
                    links=links,
                )
            )
        return results
