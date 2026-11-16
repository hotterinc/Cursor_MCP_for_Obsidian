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


def _note(tmp_path: Path, body: str) -> object:
    path = tmp_path / "Long.md"
    path.write_text(body, encoding="utf-8")
    return parse_markdown_file(path, "Long.md")


def _words(text: str) -> int:
    # Window usage of a whitespace "tokenizer": prefix + <s></s> overhead of 3.
    return len(text.split()) + 3


def test_long_section_chunks_fit_model_window(tmp_path: Path) -> None:
    body = "# Title\n\n" + "\n".join(f"line {i} " + "word " * 30 for i in range(200))
    chunks = chunk_note(
        _note(tmp_path, body),
        project_id="t",
        vault_real_path=str(tmp_path),
        token_counter=_words,
        max_input_tokens=512,
    )
    assert len(chunks) > 1
    assert all(_words(c.text) <= 512 for c in chunks)
    # Nothing lost: every source line appears in some chunk.
    joined = "\n".join(c.text for c in chunks)
    assert all(f"line {i} " in joined for i in range(200))


def test_single_huge_line_is_split(tmp_path: Path) -> None:
    body = "# Title\n\n" + " ".join(f"w{i}" for i in range(3000)) + "\n" + "x" * 50000
    chunks = chunk_note(
        _note(tmp_path, body),
        project_id="t",
        vault_real_path=str(tmp_path),
        token_counter=lambda t: max(1, len(t) // 4) + 3,
        max_input_tokens=512,
    )
    assert len(chunks) > 10
    assert all(len(c.text) // 4 + 3 <= 512 for c in chunks)
    joined = " ".join(c.text for c in chunks)
    assert "w0" in joined and "w2999" in joined


def test_small_note_is_one_chunk(tmp_path: Path) -> None:
    chunks = chunk_note(
        _note(tmp_path, "# Small\n\nJust a few words.\n"),
        project_id="t",
        vault_real_path=str(tmp_path),
        token_counter=_words,
        max_input_tokens=512,
    )
    assert len(chunks) == 1
    assert chunks[0].token_count == _words(chunks[0].text)
