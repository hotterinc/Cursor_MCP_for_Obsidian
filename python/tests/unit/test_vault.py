"""Vault validation tests."""

from pathlib import Path

from obsidian_context_mcp.core.vault import scan_markdown_files, validate_vault_path

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_vault"


def test_valid_vault_path():
    result = validate_vault_path(str(FIXTURES))
    assert result.can_read
    assert result.markdown_files_count >= 3


def test_scan_respects_exclude():
    files = scan_markdown_files(
        FIXTURES,
        include=["**/*.md"],
        exclude=[".obsidian/**", "Architecture/**"],
    )
    assert not any(f.startswith("Architecture/") for f in files)
