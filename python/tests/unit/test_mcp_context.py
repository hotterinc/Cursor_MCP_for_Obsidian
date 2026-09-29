from __future__ import annotations

from pathlib import Path

import pytest

from obsidian_context_mcp.mcp_server.context import project_root_override
from obsidian_context_mcp.mcp_server.server import call_tool
from obsidian_context_mcp.mcp_server.tools import config_get_project


@pytest.mark.asyncio
async def test_project_root_override_is_used_for_stdio_tools(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "chosen"
    project.mkdir()
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.chdir(other)
    token = project_root_override.set(str(project))
    try:
        result = await config_get_project({})
        assert Path(result["projectRoot"]).resolve() == project.resolve()
    finally:
        project_root_override.reset(token)


@pytest.mark.asyncio
async def test_stdio_tool_errors_are_mcp_errors() -> None:
    result = await call_tool("does_not_exist", {})
    assert result.isError
    assert "unknown tool" in result.content[0].text
