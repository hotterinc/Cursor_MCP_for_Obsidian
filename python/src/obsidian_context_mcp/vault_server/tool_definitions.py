"""MCP tool metadata for vault-server (scoped access)."""

from __future__ import annotations

from typing import Any

VAULT_TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "scope_get_info",
        "description": (
            "Returns the active access scope, allowed folder patterns, index status, "
            "and file counts. Call first in a new Cursor session."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "docs_search",
        "description": "Hybrid semantic + lexical search within the scope's allowed folders.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "topK": {"type": "integer", "default": 10},
                "mode": {"type": "string", "enum": ["hybrid", "semantic", "lexical"]},
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_get_context_pack",
        "description": "Build a token-budgeted context bundle for a coding task from scoped docs.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string"},
                "tokenBudget": {"type": "integer", "default": 6000},
                "topK": {"type": "integer", "default": 12},
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_read_note",
        "description": "Read a markdown note within scope. Returns content and sha256.",
        "inputSchema": {
            "type": "object",
            "properties": {"relativePath": {"type": "string"}},
            "required": ["relativePath"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_list_notes",
        "description": "List indexed notes within scope.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "tag": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_index_status",
        "description": "Check vault index job status.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "docs_reindex",
        "description": "Trigger reindex (only if scope has canReindex=true).",
        "inputSchema": {
            "type": "object",
            "properties": {"mode": {"type": "string", "enum": ["full", "incremental"]}},
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_patch_note",
        "description": "Patch a note if scope has writeAccess.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relativePath": {"type": "string"},
                "expectedSha256": {"type": "string"},
                "mode": {
                    "type": "string",
                    "enum": ["replace_exact", "unified_diff", "append_section", "upsert_section"],
                },
                "patch": {"type": "object"},
                "dryRun": {"type": "boolean"},
            },
            "required": ["relativePath", "expectedSha256", "mode", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_create_note",
        "description": "Create a note if scope has writeAccess.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relativePath": {"type": "string"},
                "content": {"type": "string"},
                "overwrite": {"type": "boolean"},
            },
            "required": ["relativePath", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_delete_note",
        "description": "Delete a note if scope has writeAccess.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "relativePath": {"type": "string"},
                "expectedSha256": {"type": "string"},
            },
            "required": ["relativePath", "expectedSha256"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_rename_note",
        "description": "Rename a note if scope has writeAccess.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "fromRelativePath": {"type": "string"},
                "toRelativePath": {"type": "string"},
                "expectedSha256": {"type": "string"},
            },
            "required": ["fromRelativePath", "toRelativePath", "expectedSha256"],
            "additionalProperties": False,
        },
    },
    {
        "name": "diagnostics_run",
        "description": "Run vault diagnostics.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]
