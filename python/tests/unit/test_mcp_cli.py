"""MCP stdout hygiene test."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PYTHON = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def test_cli_help_does_not_break():
    result = subprocess.run(
        [str(PYTHON), "-m", "obsidian_context_mcp", "--help"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent.parent),
        timeout=30,
    )
    assert result.returncode == 0
    assert "server" in result.stdout
