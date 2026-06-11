"""Indexing orchestration."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Union

from loguru import logger

from obsidian_context_mcp.core.index_serial import INDEX_SERIAL_LOCK
from obsidian_context_mcp.core.embeddings import create_embedding_provider
from obsidian_context_mcp.core.locks import ProjectLock
from obsidian_context_mcp.core.markdown_parser import parse_markdown_file
from obsidian_context_mcp.core.project import ProjectContext, compute_file_id
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import scan_markdown_files
from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.core.vault_paths import get_vault_chroma_path
from obsidian_context_mcp.core.vector_store import create_vector_store, create_vector_store_at
from obsidian_context_mcp.core.work_context import WorkContext
from obsidian_context_mcp.shared.types import IndexMode, IndexProgress, JobStatus

ProgressCallback = Callable[[IndexProgress], None]

ContextLike = Union[ProjectContext, VaultContext, WorkContext]


def _normalize_ctx(ctx: ContextLike) -> WorkContext:
    if isinstance(ctx, WorkContext):
        return ctx
    if isinstance(ctx, VaultContext):
        return ctx.work_context()
    return WorkContext.from_project(ctx)


class Indexer:
    def __init__(self, ctx: ContextLike) -> None:
        self.work = _normalize_ctx(ctx)
        self.db = SQLiteStore(self.work.db_path)
        self.db.initialize()
        if isinstance(ctx, VaultContext):
            chroma_path = get_vault_chroma_path(ctx.data_dir)
            self.vector_store = create_vector_store_at(chroma_path, self.work.context_id)
        else:
            self.vector_store = create_vector_store(self.work.context_id)
        self.embedder = create_embedding_provider(
            self.work.as_project_config(),
            self.work.context_id,
        )
        self._cancel_flag = False
        self._current_job_id: str | None = None

    def cancel(self) -> None:
        self._cancel_flag = True

    def _emit(self, callback: ProgressCallback | None, progress: IndexProgress) -> None:
        if callback:
            callback(progress)

    def index_file(self, relative_path: str) -> None:
        with INDEX_SERIAL_LOCK:
            self._index_file_unlocked(relative_path)

    def _index_file_unlocked(self, relative_path: str) -> None:
        vault_root = Path(self.work.vault_real_path)
        file_path = vault_root / relative_path
        file_id = compute_file_id(
            self.work.context_id,
            self.work.vault_real_path,
            relative_path,
        )
        if not file_path.exists():
            old_ids = self.db.delete_chunks_for_file(file_id)
            self.vector_store.delete_chunks(self.work.context_id, old_ids)
            self.db.mark_file_deleted(file_id)
            return

        note = parse_markdown_file(file_path, relative_path)
        stat = file_path.stat()
        existing_file = self.db.get_file_by_path(relative_path)
        if existing_file and existing_file["sha256"] == note.sha256:
            return

        old_rows = self.db.get_chunks_for_file(file_id)
        old_by_index = {int(r["chunk_index"]): r for r in old_rows}

        new_chunks = chunk_note(
            note,
            project_id=self.work.context_id,
            vault_real_path=self.work.vault_real_path,
        )
        new_by_index = {c.chunk_index: c for c in new_chunks}

        reuse_ids: set[str] = set()
        to_embed: list = []
        for chunk in new_chunks:
            old = old_by_index.get(chunk.chunk_index)
            if old and old["chunk_hash"] == chunk.chunk_hash and old["id"] == chunk.id:
                reuse_ids.add(chunk.id)
            else:
                to_embed.append(chunk)

        to_delete = [
            r["id"]
            for idx, r in old_by_index.items()
            if idx not in new_by_index
            or new_by_index[idx].chunk_hash != r["chunk_hash"]
            or new_by_index[idx].id != r["id"]
        ]
        if to_delete:
            self.db.delete_chunks_by_ids(to_delete)
            self.vector_store.delete_chunks(self.work.context_id, to_delete)

        self.db.upsert_file(
            file_id=file_id,
            relative_path=relative_path,
            absolute_path=str(file_path),
            real_path=os.path.realpath(file_path),
            size=stat.st_size,
            mtime_ms=int(stat.st_mtime * 1000),
            sha256=note.sha256,
            title=note.title,
            frontmatter=note.frontmatter,
            tags=note.tags,
            links=note.wikilinks,
        )

        if not new_chunks:
            return

        vectors: list[list[float]] = []
        embed_chunks: list = []
        if to_embed:
            texts = [c.text for c in to_embed]
            logger.info("Embedding {} new/changed chunks for {}", len(texts), relative_path)
            vectors = self.embedder.embed_texts(texts, is_query=False)
            embed_chunks = to_embed
            logger.info("Embedded {} vectors for {}", len(vectors), relative_path)

        for chunk in new_chunks:
            if chunk.id in reuse_ids:
                continue
            self.db.upsert_chunk(chunk, title=note.title, tags=note.tags)

        if embed_chunks:
            metadatas = [
                {
                    "chunk_id": c.id,
                    "file_id": c.file_id,
                    "relative_path": relative_path,
                    "title": note.title,
                }
                for c in embed_chunks
            ]
            self.vector_store.upsert_chunks(
                self.work.context_id,
                [c.id for c in embed_chunks],
                vectors,
                metadatas,
            )

    def run(
        self,
        mode: IndexMode = IndexMode.INCREMENTAL,
        *,
        progress_callback: ProgressCallback | None = None,
    ) -> IndexProgress:
        job_id = str(uuid.uuid4())
        self._current_job_id = job_id
        self._cancel_flag = False
        stats = {
            "files_scanned": 0,
            "files_indexed": 0,
            "files_skipped": 0,
            "files_failed": 0,
            "chunks_created": 0,
            "chunks_embedded": 0,
        }
        progress = IndexProgress(job_id=job_id, status=JobStatus.RUNNING)

        self.db.create_index_job(job_id, self.work.context_id, mode.value)

        with INDEX_SERIAL_LOCK:
            if mode == IndexMode.FULL:
                with ProjectLock(self.work.context_id, "index", timeout=5):
                    self.db.reset_all()
                    self.vector_store.reset_project(self.work.context_id)

            vault_root = Path(self.work.vault_real_path)
            md_files = scan_markdown_files(
                vault_root,
                include=self.work.include,
                exclude=self.work.exclude,
                docs_subfolder=self.work.docs_subfolder,
            )
            progress.total_files = len(md_files)
            existing = {r["relative_path"]: r for r in self.db.get_all_files()}
            self._emit(progress_callback, progress)

            for rel in md_files:
                if self._cancel_flag:
                    progress.status = JobStatus.CANCELLED
                    self.db.finish_index_job(job_id, JobStatus.CANCELLED, stats)
                    return progress

                stats["files_scanned"] += 1
                progress.files_scanned = stats["files_scanned"]
                progress.current_file = rel
                self._emit(progress_callback, progress)

                file_path = vault_root / rel
                try:
                    stat = file_path.stat()
                    mtime_ms = int(stat.st_mtime * 1000)
                    row = existing.get(rel)
                    if mode == IndexMode.INCREMENTAL and row:
                        if row["mtime_ms"] == mtime_ms and row["size"] == stat.st_size:
                            stats["files_skipped"] += 1
                            progress.files_skipped = stats["files_skipped"]
                            self._emit(progress_callback, progress)
                            continue
                        if row.get("sha256"):
                            note_path = vault_root / rel
                            from obsidian_context_mcp.core.markdown_parser import parse_markdown_file

                            current = parse_markdown_file(note_path, rel)
                            if current.sha256 == row["sha256"]:
                                stats["files_skipped"] += 1
                                progress.files_skipped = stats["files_skipped"]
                                self._emit(progress_callback, progress)
                                continue

                    self._index_file_unlocked(rel)
                    stats["files_indexed"] += 1
                    progress.files_indexed = stats["files_indexed"]
                    self._emit(progress_callback, progress)
                except Exception:
                    stats["files_failed"] += 1
                    progress.files_failed = stats["files_failed"]
                    self._emit(progress_callback, progress)

            current_set = set(md_files)
            for row in self.db.get_all_files():
                if row["relative_path"] not in current_set:
                    chunk_ids = self.db.delete_chunks_for_file(row["id"])
                    self.vector_store.delete_chunks(self.work.context_id, chunk_ids)
                    self.db.mark_file_deleted(row["id"])

        progress.status = JobStatus.COMPLETED
        self.db.finish_index_job(job_id, JobStatus.COMPLETED, stats)
        self._emit(progress_callback, progress)
        return progress
