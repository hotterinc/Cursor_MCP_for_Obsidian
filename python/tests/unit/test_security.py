"""Security boundary tests."""

from __future__ import annotations

import sys

import pytest

from obsidian_context_mcp.core.config_store import ConfigStore
from obsidian_context_mcp.core.errors import PathSecurityError, WriteAccessDeniedError
from obsidian_context_mcp.core.security import SecurityBoundary


@pytest.fixture
def vault_setup(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "note.md").write_text("# Test\n", encoding="utf-8")
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian" / "config").write_text("{}", encoding="utf-8")

    project_root = tmp_path / "project"
    project_root.mkdir()
    store = ConfigStore.for_project_root(str(project_root))
    config = store.create_or_update(str(project_root), vault_path=str(vault))
    return config, vault


def test_valid_read_path(vault_setup):
    config, _ = vault_setup
    boundary = SecurityBoundary(config)
    resolved = boundary.resolve_read_path("note.md")
    assert resolved.relative_path == "note.md"
    assert resolved.real_path.endswith("note.md")


def test_path_traversal_blocked(vault_setup):
    config, _ = vault_setup
    boundary = SecurityBoundary(config)
    with pytest.raises(PathSecurityError):
        boundary.resolve_read_path("../outside.md")


def test_non_md_blocked(vault_setup):
    config, vault = vault_setup
    (vault / "file.txt").write_text("text", encoding="utf-8")
    boundary = SecurityBoundary(config)
    with pytest.raises(PathSecurityError):
        boundary.resolve_read_path("file.txt")


def test_write_access_denied_by_default(vault_setup):
    config, _ = vault_setup
    boundary = SecurityBoundary(config)
    with pytest.raises(WriteAccessDeniedError):
        boundary.resolve_write_path("note.md")


def test_write_blocked_obsidian(vault_setup):
    config, _ = vault_setup
    config.write_access = True
    boundary = SecurityBoundary(config)
    with pytest.raises(PathSecurityError):
        boundary.resolve_write_path(".obsidian/config")


@pytest.mark.skipif(sys.platform == "win32", reason="symlink test unix only")
def test_symlink_escape_blocked(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("# Outside", encoding="utf-8")
    link = vault / "escape.md"
    link.symlink_to(outside)

    project_root = tmp_path / "project"
    project_root.mkdir()
    store = ConfigStore.for_project_root(str(project_root))
    config = store.create_or_update(str(project_root), vault_path=str(vault))
    config.write_access = True
    boundary = SecurityBoundary(config)
    with pytest.raises(PathSecurityError):
        boundary.resolve_read_path("escape.md")


def test_read_only_scope_cannot_borrow_project_write_access(tmp_path):
    from obsidian_context_mcp.core.errors import WriteAccessDeniedError
    from obsidian_context_mcp.core.security import ScopeBoundary
    from obsidian_context_mcp.shared.types import AccessScope, ProjectConfig
    config = ProjectConfig(project_root=str(tmp_path), project_real_path=str(tmp_path),
                           project_name="test", vault_path=str(tmp_path),
                           vault_real_path=str(tmp_path), write_access=True)
    boundary = ScopeBoundary(SecurityBoundary(config), AccessScope(
        id="read", name="Read", include=["**/*.md"], token="t", write_access=False))
    with pytest.raises(WriteAccessDeniedError):
        boundary.resolve_write_path("note.md")
