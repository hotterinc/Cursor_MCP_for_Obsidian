"""Tests for access scope path filtering."""

from obsidian_context_mcp.core.scope_filter import filter_paths, path_in_scope
from obsidian_context_mcp.shared.types import AccessScope


def test_path_in_scope_include():
    scope = AccessScope(
        id="test",
        name="Test",
        include=["Projects/A/**"],
        exclude=[],
        token="ocm_test",
    )
    assert path_in_scope("Projects/A/note.md", scope)
    assert not path_in_scope("Projects/B/note.md", scope)


def test_path_in_scope_exclude():
    scope = AccessScope(
        id="test",
        name="Test",
        include=["Projects/**"],
        exclude=["Projects/_private/**"],
        token="ocm_test",
    )
    assert path_in_scope("Projects/A/note.md", scope)
    assert not path_in_scope("Projects/_private/secret.md", scope)


def test_filter_paths():
    scope = AccessScope(
        id="test",
        name="Test",
        include=["A/**"],
        exclude=[],
        token="ocm_test",
    )
    result = filter_paths(["A/1.md", "B/2.md"], scope)
    assert result == ["A/1.md"]
