"""MCP client configuration snippets for Claude Code and Claude Desktop."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

SERVER_NAME = "obsidian-context"
SCOPE_TOKEN_ENV = "OBSIDIAN_CONTEXT_SCOPE_TOKEN"


def claude_code_configs(port: int, token: str) -> dict[str, Any]:
    """Claude Code connects to Streamable HTTP /mcp directly."""
    url = f"http://127.0.0.1:{port}/mcp"
    # Double quotes work in bash, zsh, cmd and PowerShell; tokens are URL-safe base64.
    command = (
        f"claude mcp add --transport http --scope user {SERVER_NAME} {url} "
        f'--header "Authorization: Bearer {token}"'
    )
    # For a repository's .mcp.json: Claude Code expands ${VAR} at startup, so the
    # file can be committed without the token.
    project = {
        "mcpServers": {
            SERVER_NAME: {
                "type": "http",
                "url": url,
                "headers": {"Authorization": f"Bearer ${{{SCOPE_TOKEN_ENV}}}"},
            }
        }
    }
    return {"command": command, "projectConfig": project, "tokenEnvVar": SCOPE_TOKEN_ENV}


def proxy_launch(data_dir: Path) -> tuple[str, list[str]]:
    """Command that starts this build's stdio proxy (frozen sidecar or dev venv)."""
    args = ["stdio-proxy", "--data-dir", str(data_dir)]
    if getattr(sys, "frozen", False):
        return sys.executable, args
    return sys.executable, ["-m", "obsidian_context_mcp", *args]


def claude_desktop_entry(data_dir: Path, token: str) -> dict[str, Any]:
    """Claude Desktop only starts stdio servers, so it launches our proxy.

    The proxy reads the current port from runtime.json, so the entry survives
    port changes. Desktop does not inherit the login shell environment, hence
    the token sits in the entry's env block.
    """
    command, args = proxy_launch(data_dir)
    return {"command": command, "args": args, "env": {SCOPE_TOKEN_ENV: token}}


def claude_desktop_config_path(platform: str | None = None) -> Path:
    platform = platform or sys.platform
    home = Path.home()
    if platform == "darwin":
        base = home / "Library" / "Application Support"
    elif platform == "win32":
        base = Path(os.environ.get("APPDATA") or home / "AppData" / "Roaming")
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
    return base / "Claude" / "claude_desktop_config.json"


class DesktopConfigError(ValueError):
    pass


def install_claude_desktop_entry(config_path: Path, entry: dict[str, Any]) -> bool:
    """Add or replace our server in claude_desktop_config.json, keeping everything else.

    Returns True when the file changed. Refuses to touch a file it cannot parse.
    """
    data: dict[str, Any] = {}
    original: str | None = None
    if config_path.exists():
        original = config_path.read_text(encoding="utf-8")
        if original.strip():
            try:
                parsed = json.loads(original)
            except json.JSONDecodeError as exc:
                raise DesktopConfigError(
                    f"{config_path} is not valid JSON (line {exc.lineno}); fix it or add the entry by hand"
                ) from exc
            if not isinstance(parsed, dict):
                raise DesktopConfigError(f"{config_path} must contain a JSON object")
            data = parsed
    servers = data.get("mcpServers")
    if servers is None:
        servers = data["mcpServers"] = {}
    if not isinstance(servers, dict):
        raise DesktopConfigError(f'"mcpServers" in {config_path} must be an object')
    if servers.get(SERVER_NAME) == entry:
        return False
    servers[SERVER_NAME] = entry

    config_path.parent.mkdir(parents=True, exist_ok=True)
    if original is not None:
        config_path.with_name(config_path.name + ".bak").write_text(original, encoding="utf-8")
    temporary = config_path.with_name(config_path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if sys.platform != "win32":
        temporary.chmod(0o600)  # the entry carries a scope token
    temporary.replace(config_path)
    return True

