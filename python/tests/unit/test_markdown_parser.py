"""Markdown parser tests."""

from pathlib import Path

from obsidian_context_mcp.core.markdown_parser import parse_markdown_file

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_vault"


def test_frontmatter_parsed():
    note = parse_markdown_file(FIXTURES / "Architecture" / "API.md", "Architecture/API.md")
    assert note.title == "Архитектура API"
    assert "backend" in note.tags
    assert "Auth Guide" in note.wikilinks


def test_headings_parsed():
    note = parse_markdown_file(FIXTURES / "Architecture" / "API.md", "Architecture/API.md")
    assert len(note.headings) >= 2
    assert any(h.text == "Аутентификация" for h in note.headings)


def test_wikilinks_and_links():
    note = parse_markdown_file(FIXTURES / "Getting Started.md", "Getting Started.md")
    assert "Architecture/API" in note.wikilinks
    assert any("Setup.md" in link for link in note.md_links)
