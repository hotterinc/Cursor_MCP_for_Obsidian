"""Claude Code / Claude Desktop config generation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from obsidian_context_mcp.vault_server.client_configs import (
    SERVER_NAME,
    DesktopConfigError,
    claude_code_configs,
    claude_desktop_config_path,
    claude_desktop_entry,
    install_claude_desktop_entry,
)


def test_claude_code_command_and_project_config() -> None:
    cfg = claude_code_configs(18432, "ocm_secret")
    assert cfg["command"] == (
        "claude mcp add --transport http --scope user obsidian-context "
        'http://127.0.0.1:18432/mcp --header "Authorization: Bearer ocm_secret"'
    )
    server = cfg["projectConfig"]["mcpServers"][SERVER_NAME]
    assert server == {
        "type": "http",
        "url": "http://127.0.0.1:18432/mcp",
        "headers": {"Authorization": "Bearer ${OBSIDIAN_CONTEXT_SCOPE_TOKEN}"},
    }
    assert "ocm_secret" not in json.dumps(cfg["projectConfig"])


def test_desktop_entry_launches_proxy_with_data_dir(tmp_path: Path) -> None:
    entry = claude_desktop_entry(tmp_path, "ocm_secret")
    assert entry["command"] == sys.executable
    assert entry["args"][-3:] == ["stdio-proxy", "--data-dir", str(tmp_path)]
    assert entry["env"] == {"OBSIDIAN_CONTEXT_SCOPE_TOKEN": "ocm_secret"}


def test_desktop_entry_uses_frozen_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", "/plugin/bin/obsidian-context-mcp")
    entry = claude_desktop_entry(tmp_path, "t")
    assert entry["command"] == "/plugin/bin/obsidian-context-mcp"
    assert entry["args"] == ["stdio-proxy", "--data-dir", str(tmp_path)]


@pytest.mark.parametrize(
    ("platform", "suffix"),
    [
        ("darwin", "Library/Application Support/Claude/claude_desktop_config.json"),
        ("linux", ".config/Claude/claude_desktop_config.json"),
    ],
)
def test_desktop_config_path(platform: str, suffix: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert claude_desktop_config_path(platform).as_posix().endswith(suffix)


def test_desktop_config_path_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    assert claude_desktop_config_path("win32") == tmp_path / "Claude" / "claude_desktop_config.json"


def test_install_creates_file(tmp_path: Path) -> None:
    path = tmp_path / "Claude" / "claude_desktop_config.json"
    assert install_claude_desktop_entry(path, {"command": "x"})
    assert json.loads(path.read_text()) == {"mcpServers": {SERVER_NAME: {"command": "x"}}}
    assert not path.with_name(path.name + ".bak").exists()


def test_install_keeps_other_servers_and_settings(tmp_path: Path) -> None:
    path = tmp_path / "claude_desktop_config.json"
    original = {"globalShortcut": "Ctrl+Space", "mcpServers": {"other": {"command": "y"}}}
    path.write_text(json.dumps(original))
    assert install_claude_desktop_entry(path, {"command": "x"})
    data = json.loads(path.read_text())
    assert data["globalShortcut"] == "Ctrl+Space"
    assert data["mcpServers"] == {"other": {"command": "y"}, SERVER_NAME: {"command": "x"}}
    assert json.loads(path.with_name(path.name + ".bak").read_text()) == original
    # Second install with the same entry is a no-op.
    assert not install_claude_desktop_entry(path, {"command": "x"})


@pytest.mark.parametrize("content", ["{ broken", "[]", '{"mcpServers": []}'])
def test_install_refuses_unexpected_content(tmp_path: Path, content: str) -> None:
    path = tmp_path / "claude_desktop_config.json"
    path.write_text(content)
    with pytest.raises(DesktopConfigError):
        install_claude_desktop_entry(path, {"command": "x"})
    assert path.read_text() == content


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX permissions")
def test_install_restricts_permissions(tmp_path: Path) -> None:
    path = tmp_path / "claude_desktop_config.json"
    install_claude_desktop_entry(path, {"command": "x", "env": {"T": "secret"}})
    assert path.stat().st_mode & 0o077 == 0
