"""FTS rows must retain chunk identifiers for hybrid retrieval."""

from __future__ import annotations

from obsidian_context_mcp.core.sqlite_store import SQLiteStore


def test_fts_search_returns_chunk_id_and_supports_delete(tmp_path):
    store = SQLiteStore(tmp_path / "db.sqlite")
    store.initialize()
    store.conn.execute(
        "INSERT INTO fts_chunks (chunk_id, text, title, heading_path, tags) "
        "VALUES (?, ?, ?, ?, ?)",
        ("chunk-1", "Искусственная заметка", "Проверка MCP", "", ""),
    )
    store.conn.commit()

    assert store.fts_search("Искусственная заметка")[0]["chunk_id"] == "chunk-1"

    store.conn.execute("DELETE FROM fts_chunks WHERE chunk_id = ?", ("chunk-1",))
    store.conn.commit()
    assert store.fts_search("Искусственная заметка") == []


def test_initialize_migrates_contentless_fts_and_rebuilds_rows(tmp_path):
    db_path = tmp_path / "db.sqlite"
    store = SQLiteStore(db_path)
    store.initialize()
    store.conn.execute("DROP TABLE fts_chunks")
    store.conn.execute(
        "CREATE VIRTUAL TABLE fts_chunks USING fts5("
        "chunk_id UNINDEXED, text, title, heading_path, tags, "
        "content='', contentless_delete=1)"
    )
    store.conn.execute(
        "INSERT INTO files (id, relative_path, title) VALUES (?, ?, ?)",
        ("file-1", "Проверка MCP.md", "Проверка MCP"),
    )
    store.conn.execute(
        "INSERT INTO chunks (id, file_id, text, heading_path_json) VALUES (?, ?, ?, ?)",
        ("chunk-1", "file-1", "Искусственная заметка", "[]"),
    )
    store.conn.execute(
        "INSERT INTO fts_chunks (chunk_id, text, title, heading_path, tags) "
        "VALUES (?, ?, ?, ?, ?)",
        ("chunk-1", "Искусственная заметка", "Проверка MCP", "", ""),
    )
    store.conn.commit()
    store.close()

    migrated = SQLiteStore(db_path)
    migrated.initialize()
    assert migrated.fts_search("Искусственная заметка")[0]["chunk_id"] == "chunk-1"
