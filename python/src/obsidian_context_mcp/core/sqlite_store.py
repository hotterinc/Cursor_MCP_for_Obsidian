"""SQLite metadata store with FTS5."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from obsidian_context_mcp.shared.types import ChunkRecord, JobStatus


class SQLiteStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
        return self._conn

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def initialize(self) -> None:
        c = self.conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                relative_path TEXT NOT NULL UNIQUE,
                absolute_path TEXT,
                real_path TEXT,
                size INTEGER,
                mtime_ms INTEGER,
                sha256 TEXT,
                title TEXT,
                frontmatter_json TEXT,
                tags_json TEXT,
                links_json TEXT,
                created_at TEXT,
                updated_at TEXT,
                indexed_at TEXT,
                deleted_at TEXT
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                file_id TEXT NOT NULL,
                chunk_index INTEGER,
                chunk_hash TEXT,
                heading_path_json TEXT,
                heading_level INTEGER,
                text TEXT,
                token_count INTEGER,
                start_line INTEGER,
                end_line INTEGER,
                metadata_json TEXT,
                embedding_status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (file_id) REFERENCES files(id)
            );

            CREATE TABLE IF NOT EXISTS operations (
                id TEXT PRIMARY KEY,
                type TEXT,
                file_id TEXT,
                relative_path TEXT,
                old_hash TEXT,
                new_hash TEXT,
                status TEXT,
                error TEXT,
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS index_jobs (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                mode TEXT,
                status TEXT,
                started_at TEXT,
                finished_at TEXT,
                stats_json TEXT,
                error TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                chunk_id UNINDEXED,
                text,
                title,
                heading_path,
                tags,
                content='',
                contentless_delete=1
            );
            """
        )
        c.commit()

    def upsert_file(
        self,
        *,
        file_id: str,
        relative_path: str,
        absolute_path: str,
        real_path: str,
        size: int,
        mtime_ms: int,
        sha256: str,
        title: str,
        frontmatter: dict,
        tags: list[str],
        links: list[str],
    ) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self.conn.execute(
            """
            INSERT INTO files (id, relative_path, absolute_path, real_path, size, mtime_ms,
                sha256, title, frontmatter_json, tags_json, links_json, created_at, updated_at, indexed_at, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(id) DO UPDATE SET
                relative_path=excluded.relative_path,
                absolute_path=excluded.absolute_path,
                real_path=excluded.real_path,
                size=excluded.size,
                mtime_ms=excluded.mtime_ms,
                sha256=excluded.sha256,
                title=excluded.title,
                frontmatter_json=excluded.frontmatter_json,
                tags_json=excluded.tags_json,
                links_json=excluded.links_json,
                updated_at=excluded.updated_at,
                indexed_at=excluded.indexed_at,
                deleted_at=NULL
            """,
            (
                file_id,
                relative_path,
                absolute_path,
                real_path,
                size,
                mtime_ms,
                sha256,
                title,
                json.dumps(frontmatter),
                json.dumps(tags),
                json.dumps(links),
                now,
                now,
                now,
            ),
        )
        self.conn.commit()

    def get_file_by_path(self, relative_path: str) -> sqlite3.Row | None:
        row = self.conn.execute(
            "SELECT * FROM files WHERE relative_path = ? AND deleted_at IS NULL",
            (relative_path,),
        ).fetchone()
        return row

    def get_all_files(self) -> list[sqlite3.Row]:
        return list(
            self.conn.execute("SELECT * FROM files WHERE deleted_at IS NULL").fetchall()
        )

    def mark_file_deleted(self, file_id: str) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self.conn.execute(
            "UPDATE files SET deleted_at = ? WHERE id = ?",
            (now, file_id),
        )
        self.conn.commit()

    def delete_chunks_for_file(self, file_id: str) -> list[str]:
        rows = self.conn.execute(
            "SELECT id FROM chunks WHERE file_id = ?", (file_id,)
        ).fetchall()
        chunk_ids = [r["id"] for r in rows]
        self.conn.execute("DELETE FROM chunks WHERE file_id = ?", (file_id,))
        for cid in chunk_ids:
            self.conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (cid,))
        self.conn.commit()
        return chunk_ids

    def upsert_chunk(self, chunk: ChunkRecord, *, title: str, tags: list[str]) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        heading_path = " > ".join(chunk.heading_path)
        self.conn.execute(
            """
            INSERT INTO chunks (id, file_id, chunk_index, chunk_hash, heading_path_json,
                heading_level, text, token_count, start_line, end_line, metadata_json,
                embedding_status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'embedded', ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                text=excluded.text, chunk_hash=excluded.chunk_hash,
                heading_path_json=excluded.heading_path_json,
                embedding_status='embedded', updated_at=excluded.updated_at
            """,
            (
                chunk.id,
                chunk.file_id,
                chunk.chunk_index,
                chunk.chunk_hash,
                json.dumps(chunk.heading_path),
                chunk.heading_level,
                chunk.text,
                chunk.token_count,
                chunk.start_line,
                chunk.end_line,
                json.dumps(chunk.metadata),
                now,
                now,
            ),
        )
        self.conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", (chunk.id,))
        self.conn.execute(
            "INSERT INTO fts_chunks (chunk_id, text, title, heading_path, tags) VALUES (?, ?, ?, ?, ?)",
            (chunk.id, chunk.text, title, heading_path, " ".join(tags)),
        )
        self.conn.commit()

    def fts_search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        try:
            rows = self.conn.execute(
                """
                SELECT chunk_id, bm25(fts_chunks) as score, text, title, heading_path, tags
                FROM fts_chunks
                WHERE fts_chunks MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
        return [dict(r) for r in rows]

    def get_chunk_with_file(self, chunk_id: str) -> dict[str, Any] | None:
        row = self.conn.execute(
            """
            SELECT c.*, f.relative_path, f.title as file_title, f.tags_json, f.links_json
            FROM chunks c JOIN files f ON c.file_id = f.id
            WHERE c.id = ? AND f.deleted_at IS NULL
            """,
            (chunk_id,),
        ).fetchone()
        return dict(row) if row else None

    def create_index_job(self, job_id: str, project_id: str, mode: str) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self.conn.execute(
            "INSERT INTO index_jobs (id, project_id, mode, status, started_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, project_id, mode, JobStatus.RUNNING.value, now),
        )
        self.conn.commit()

    def finish_index_job(self, job_id: str, status: JobStatus, stats: dict, error: str | None = None) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self.conn.execute(
            "UPDATE index_jobs SET status=?, finished_at=?, stats_json=?, error=? WHERE id=?",
            (status.value, now, json.dumps(stats), error, job_id),
        )
        self.conn.commit()

    def log_operation(
        self,
        op_id: str,
        op_type: str,
        file_id: str,
        relative_path: str,
        old_hash: str,
        new_hash: str,
        status: str,
        error: str | None = None,
    ) -> None:
        now = datetime.utcnow().isoformat() + "Z"
        self.conn.execute(
            """
            INSERT INTO operations (id, type, file_id, relative_path, old_hash, new_hash, status, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (op_id, op_type, file_id, relative_path, old_hash, new_hash, status, error, now),
        )
        self.conn.commit()

    def list_notes(
        self,
        *,
        query: str | None = None,
        tag: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM files WHERE deleted_at IS NULL"
        params: list[Any] = []
        if query:
            sql += " AND (title LIKE ? OR relative_path LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
        if tag:
            sql += " AND tags_json LIKE ?"
            params.append(f'%"{tag}"%')
        sql += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def reset_all(self) -> None:
        self.conn.executescript(
            "DELETE FROM fts_chunks; DELETE FROM chunks; DELETE FROM files; DELETE FROM operations;"
        )
        self.conn.commit()
