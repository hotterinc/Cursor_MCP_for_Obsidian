"""Chunker tests."""

from pathlib import Path

from obsidian_context_mcp.core.chunker import chunk_note
from obsidian_context_mcp.core.markdown_parser import parse_markdown_file

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_vault"


def test_chunker_preserves_heading_paths():
    note = parse_markdown_file(FIXTURES / "Architecture" / "API.md", "Architecture/API.md")
    chunks = chunk_note(note, project_id="test", vault_real_path="/vault")
    assert len(chunks) >= 1
    assert chunks[0].heading_path
