"""MCP stdio server."""

from __future__ import annotations

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Prompt, PromptMessage, Resource, TextContent, Tool

from obsidian_context_mcp.core.logging import get_logger, setup_logging
from obsidian_context_mcp.core.project import get_project_context
from obsidian_context_mcp.mcp_server import prompts, resources, tools

logger = get_logger()
server = Server("obsidian-context-mcp")

TOOL_DEFINITIONS: list[tuple[str, str, dict]] = [
    ("config_open_gui", "Open desktop configuration GUI", {"type": "object", "properties": {"projectRoot": {"type": "string"}}, "additionalProperties": False}),
    ("config_get_project", "Get project configuration status", {"type": "object", "properties": {"projectRoot": {"type": "string"}}, "additionalProperties": False}),
    ("config_set_vault_path", "Set Obsidian vault path", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "vaultPath": {"type": "string"}, "writeAccess": {"type": "boolean"}, "include": {"type": "array", "items": {"type": "string"}}, "exclude": {"type": "array", "items": {"type": "string"}}}, "required": ["projectRoot", "vaultPath"], "additionalProperties": False}),
    ("docs_reindex", "Reindex documentation", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "mode": {"type": "string", "enum": ["incremental", "full"]}, "force": {"type": "boolean"}}, "additionalProperties": False}),
    ("docs_index_status", "Get index status", {"type": "object", "properties": {"projectRoot": {"type": "string"}}, "additionalProperties": False}),
    ("docs_search", "Search documentation", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "query": {"type": "string"}, "topK": {"type": "integer"}, "mode": {"type": "string", "enum": ["hybrid", "semantic", "lexical"]}, "filters": {"type": "object"}}, "required": ["query"], "additionalProperties": False}),
    ("docs_get_context_pack", "Build context pack for task", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "task": {"type": "string"}, "tokenBudget": {"type": "integer"}, "topK": {"type": "integer"}, "includeLinked": {"type": "boolean"}, "includeFrontmatter": {"type": "boolean"}}, "required": ["task"], "additionalProperties": False}),
    ("docs_read_note", "Read a note", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "relativePath": {"type": "string"}}, "required": ["relativePath"], "additionalProperties": False}),
    ("docs_list_notes", "List notes", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "query": {"type": "string"}, "tag": {"type": "string"}, "limit": {"type": "integer"}}, "additionalProperties": False}),
    ("docs_patch_note", "Patch a note", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "relativePath": {"type": "string"}, "expectedSha256": {"type": "string"}, "mode": {"type": "string"}, "patch": {"type": "object"}, "dryRun": {"type": "boolean"}, "createBackup": {"type": "boolean"}}, "required": ["relativePath", "expectedSha256", "mode", "patch"], "additionalProperties": False}),
    ("docs_create_note", "Create a note", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "relativePath": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}, "createBackup": {"type": "boolean"}}, "required": ["relativePath", "content"], "additionalProperties": False}),
    ("docs_delete_note", "Delete a note", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "relativePath": {"type": "string"}, "expectedSha256": {"type": "string"}, "createBackup": {"type": "boolean"}}, "required": ["relativePath", "expectedSha256"], "additionalProperties": False}),
    ("docs_rename_note", "Rename a note", {"type": "object", "properties": {"projectRoot": {"type": "string"}, "fromRelativePath": {"type": "string"}, "toRelativePath": {"type": "string"}, "expectedSha256": {"type": "string"}, "updateWikilinks": {"type": "boolean"}}, "required": ["fromRelativePath", "toRelativePath", "expectedSha256"], "additionalProperties": False}),
    ("diagnostics_run", "Run diagnostics", {"type": "object", "properties": {"projectRoot": {"type": "string"}}, "additionalProperties": False}),
]

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


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name=name, description=desc, inputSchema=schema)
        for name, desc, schema in TOOL_DEFINITIONS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    handler = TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
    try:
        result = await handler(args)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as exc:
        logger.exception("Tool error: {}", name)
        return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]


@server.list_resources()
async def list_resources() -> list[Resource]:
    return [
        Resource(uri="obsidian-context://project/current/status", name="Project Status", mimeType="application/json"),
        Resource(uri="obsidian-context://project/current/config", name="Project Config", mimeType="application/json"),
        Resource(uri="obsidian-context://project/current/index-stats", name="Index Stats", mimeType="application/json"),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    return await resources.read_resource(uri)


@server.list_prompts()
async def list_prompts() -> list[Prompt]:
    return [
        Prompt(name="use_project_docs", description="Use project documentation before coding"),
        Prompt(name="update_project_docs", description="Update docs after code changes"),
        Prompt(name="summarize_project_docs", description="Summarize documentation area"),
    ]


@server.get_prompt()
async def get_prompt(name: str, arguments: dict[str, str] | None = None) -> Any:
    content_map = {
        "use_project_docs": prompts.USE_PROJECT_DOCS,
        "update_project_docs": prompts.UPDATE_PROJECT_DOCS,
        "summarize_project_docs": prompts.SUMMARIZE_PROJECT_DOCS,
    }
    text = content_map.get(name, "")
    return Prompt(
        name=name,
        description=name,
        messages=[PromptMessage(role="user", content=TextContent(type="text", text=text))],
    )


async def run_mcp_server(project_root: str) -> None:
    setup_logging(level="INFO")
    ctx = get_project_context(project_root)
    logger.info("MCP server starting for project {}", ctx.project_id)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())
