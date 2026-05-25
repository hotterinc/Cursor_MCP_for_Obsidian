"""MCP stdio server."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import GetPromptResult, Prompt, PromptMessage, Resource, TextContent, Tool

from obsidian_context_mcp.core.logging import get_logger, setup_logging
from obsidian_context_mcp.mcp_server import prompts, resources, tools
from obsidian_context_mcp.mcp_server.tool_definitions import TOOL_DEFINITIONS

logger = get_logger()
server = Server("obsidian-context-mcp")

TOOL_HANDLERS = {
    "config_open_gui": tools.config_open_gui,
    "config_get_project": tools.config_get_project,
    "config_set_vault_path": tools.config_set_vault_path,
    "docs_reindex": tools.docs_reindex,
    "docs_index_status": tools.docs_index_status,
    "docs_search": tools.docs_search,
    "docs_get_context_pack": tools.docs_get_context_pack,
    "docs_read_note": tools.docs_read_note,
    "docs_list_notes": tools.docs_list_notes,
    "docs_patch_note": tools.docs_patch_note,
    "docs_create_note": tools.docs_create_note,
    "docs_delete_note": tools.docs_delete_note,
    "docs_rename_note": tools.docs_rename_note,
    "diagnostics_run": tools.diagnostics_run,
}


def _run_tool_handler(handler: Callable[..., Awaitable[Any]], args: dict[str, Any]) -> Any:
    """Run tool handler off the MCP event loop (embedding/search can block for minutes)."""
    return asyncio.run(handler(args))


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name=spec["name"], description=spec["description"], inputSchema=spec["inputSchema"])
        for spec in TOOL_DEFINITIONS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
    try:
        result = await asyncio.to_thread(_run_tool_handler, handler, args)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as exc:
        logger.exception("Tool error: {}", name)
        return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(
            uri="obsidian-context://project/current/status",
            name="Project Status",
            description="JSON snapshot: configured flag, vault path, index readiness for the active project.",
            mimeType="application/json",
        ),
        Resource(
            uri="obsidian-context://project/current/config",
            name="Project Config",
            description="Full project.json settings: vault, include/exclude globs, write access, embeddings.",
            mimeType="application/json",
        ),
        Resource(
            uri="obsidian-context://project/current/index-stats",
            name="Index Stats",
            description="Indexed file and chunk counts from the local SQLite/vector store.",
            mimeType="application/json",
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    return await resources.read_resource(uri)


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(
            name="use_project_docs",
            description=(
                "Instruct the agent to load Obsidian documentation context before coding "
                "(via docs_get_context_pack or docs_search)."
            ),
        ),
        Prompt(
            name="update_project_docs",
            description=(
                "Instruct the agent to update Obsidian notes after code changes "
                "using docs_read_note + docs_patch_note with sha256 checks."
            ),
        ),
        Prompt(
            name="summarize_project_docs",
            description="Instruct the agent to summarize a documentation area from the indexed vault.",
        ),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> GetPromptResult:
    content_map = {
        "use_project_docs": prompts.USE_PROJECT_DOCS,
        "update_project_docs": prompts.UPDATE_PROJECT_DOCS,
        "summarize_project_docs": prompts.SUMMARIZE_PROJECT_DOCS,
    }
    text = content_map.get(name, "")
    return GetPromptResult(
        description=name,
        messages=[PromptMessage(role="user", content=TextContent(type="text", text=text))],
    )


async def run_mcp_server(project_root: str | None = None) -> None:
    setup_logging(level="INFO")
    if project_root:
        logger.info("MCP server starting (project root override: {})", project_root)
    else:
        logger.info("MCP server starting in multi-project mode")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
