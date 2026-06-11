"""Vector store interface and ChromaDB implementation."""

from __future__ import annotations

import contextlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import chromadb

from obsidian_context_mcp.core.app_paths import get_project_chroma_path


class VectorStore(ABC):
    @abstractmethod
    def upsert_chunks(
        self,
        project_id: str,
        chunk_ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def delete_chunks(self, project_id: str, chunk_ids: list[str]) -> None:
        raise NotImplementedError

    @abstractmethod
    def search(
        self,
        project_id: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        raise NotImplementedError

    @abstractmethod
    def reset_project(self, project_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self, project_id: str) -> bool:
        raise NotImplementedError


class ChromaVectorStore(VectorStore):
    def __init__(self, persist_dir: str) -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)

    def _collection(self, project_id: str):
        return self._client.get_or_create_collection(
            name=f"project_{project_id[:16]}",
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        project_id: str,
        chunk_ids: list[str],
        vectors: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not chunk_ids:
            return
        col = self._collection(project_id)
        # Chroma metadata values must be str/int/float/bool
        clean_meta = []
        for m in metadatas:
            clean_meta.append(
                {k: (v if isinstance(v, (str, int, float, bool)) else str(v)) for k, v in m.items()}
            )
        col.upsert(ids=chunk_ids, embeddings=vectors, metadatas=clean_meta)

    def delete_chunks(self, project_id: str, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        col = self._collection(project_id)
        with contextlib.suppress(Exception):
            col.delete(ids=chunk_ids)

    def search(
        self,
        project_id: str,
        vector: list[float],
        top_k: int,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        col = self._collection(project_id)
        where = filters if filters else None
        try:
            results = col.query(
                query_embeddings=[vector],
                n_results=top_k,
                where=where,
            )
        except Exception:
            return []
        items = []
        if not results["ids"] or not results["ids"][0]:
            return items
        for i, cid in enumerate(results["ids"][0]):
            dist = results["distances"][0][i] if results.get("distances") else 0
            score = 1.0 - dist if dist is not None else 0.5
            meta = results["metadatas"][0][i] if results.get("metadatas") else {}
            items.append({"chunk_id": cid, "score": score, "metadata": meta or {}})
        return items

    def reset_project(self, project_id: str) -> None:
        with contextlib.suppress(Exception):
            self._client.delete_collection(f"project_{project_id[:16]}")

    def healthcheck(self, project_id: str) -> bool:
        try:
            self._collection(project_id)
            return True
        except Exception:
            return False


def create_vector_store(project_id: str) -> VectorStore:
    path = str(get_project_chroma_path(project_id))
    return ChromaVectorStore(path)


def create_vector_store_at(chroma_path: Path, context_id: str) -> VectorStore:
    store = ChromaVectorStore(str(chroma_path))
    # touch collection
    store.healthcheck(context_id)
    return store
