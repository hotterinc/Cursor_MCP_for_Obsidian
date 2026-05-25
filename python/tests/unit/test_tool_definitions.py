"""MCP tool definition consistency."""

from obsidian_context_mcp.mcp_server.server import TOOL_HANDLERS
from obsidian_context_mcp.mcp_server.tool_definitions import TOOL_DEFINITIONS


def test_tool_definitions_match_handlers() -> None:
    names = {spec["name"] for spec in TOOL_DEFINITIONS}
    assert names == set(TOOL_HANDLERS.keys())


def test_tool_descriptions_are_informative() -> None:
    for spec in TOOL_DEFINITIONS:
        assert len(spec["description"]) >= 40, spec["name"]
        assert spec["inputSchema"]["type"] == "object"
