"""Indexing orchestration."""

from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from pathlib import Path

from obsidian_context_mcp.core.chunker import chunk_note
from obsidian_context_mcp.core.embeddings import create_embedding_provider
from obsidian_context_mcp.core.locks import ProjectLock
from obsidian_context_mcp.core.markdown_parser import parse_markdown_file
from obsidian_context_mcp.core.project import ProjectContext, compute_file_id
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import scan_markdown_files
from obsidian_context_mcp.core.vector_store import create_vector_store
from obsidian_context_mcp.shared.types import IndexMode, IndexProgress, JobStatus

ProgressCallback = Callable[[IndexProgress], None]


class Indexer:
    def __init__(self, ctx: ProjectContext) -> None:
        self.ctx = ctx
        self.config = ctx.config_store.require_configured()
        self.db = SQLiteStore(ctx.config_store.config_path.parent / "db.sqlite")
        self.db.initialize()
        self.vector_store = create_vector_store(ctx.project_id)
        self.embedder = create_embedding_provider(self.config, ctx.project_id)
        self._cancel_flag = False
        self._current_job_id: str | None = None

    def cancel(self) -> None:
        self._cancel_flag = True

    def _emit(self, callback: ProgressCallback | None, progress: IndexProgress) -> None:
        if callback:
            callback(progress)

    def index_file(self, relative_path: str) -> None:
        vault_root = Path(self.config.vault_real_path or self.config.vault_path or "")
        file_path = vault_root / relative_path
        if not file_path.exists():
            file_id = compute_file_id(
                self.ctx.project_id,
                self.config.vault_real_path or "",
                relative_path,
            )
            self.db.delete_chunks_for_file(file_id)
            self.db.mark_file_deleted(file_id)
            return

        note = parse_markdown_file(file_path, relative_path)
        stat = file_path.stat()
        file_id = compute_file_id(
            self.ctx.project_id,
            self.config.vault_real_path or "",
            relative_path,
        )
        old_chunk_ids = self.db.delete_chunks_for_file(file_id)
        self.vector_store.delete_chunks(self.ctx.project_id, old_chunk_ids)

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

        chunks = chunk_note(
            note,
            project_id=self.ctx.project_id,
            vault_real_path=self.config.vault_real_path or "",
        )
        if not chunks:
            return

        texts = [c.text for c in chunks]
        vectors = self.embedder.embed_texts(texts, is_query=False)
        metadatas = [
            {
                "chunk_id": c.id,
                "file_id": c.file_id,
                "relative_path": relative_path,
                "title": note.title,
            }
            for c in chunks
        ]
        for chunk in chunks:
            self.db.upsert_chunk(chunk, title=note.title, tags=note.tags)
        self.vector_store.upsert_chunks(
            self.ctx.project_id,
            [c.id for c in chunks],
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

        self.db.create_index_job(job_id, self.ctx.project_id, mode.value)

        if mode == IndexMode.FULL:
            with ProjectLock(self.ctx.project_id, "index", timeout=5):
                self.db.reset_all()
                self.vector_store.reset_project(self.ctx.project_id)

        vault_root = Path(self.config.vault_real_path or self.config.vault_path or "")
        md_files = scan_markdown_files(
            vault_root,
            include=self.config.include,
            exclude=self.config.exclude,
            docs_subfolder=self.config.docs_subfolder,
        )
        existing = {r["relative_path"]: r for r in self.db.get_all_files()}

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
                mtime_sha = existing.get(rel)
                if (
                    mode == IndexMode.INCREMENTAL
                    and mtime_sha
                    and mtime_sha["mtime_ms"] == mtime_ms
                    and mtime_sha["size"] == stat.st_size
                ):
                    stats["files_skipped"] += 1
                    progress.files_skipped = stats["files_skipped"]
                    continue

                self.index_file(rel)
                stats["files_indexed"] += 1
                progress.files_indexed = stats["files_indexed"]
            except Exception:
                stats["files_failed"] += 1
                progress.files_failed = stats["files_failed"]

        # Cleanup deleted files
        current_set = set(md_files)
        for row in self.db.get_all_files():
            if row["relative_path"] not in current_set:
                chunk_ids = self.db.delete_chunks_for_file(row["id"])
                self.vector_store.delete_chunks(self.ctx.project_id, chunk_ids)
                self.db.mark_file_deleted(row["id"])

        progress.status = JobStatus.COMPLETED
        self.db.finish_index_job(job_id, JobStatus.COMPLETED, stats)
        self._emit(progress_callback, progress)
        return progress
