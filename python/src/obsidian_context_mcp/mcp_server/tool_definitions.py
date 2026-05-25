"""MCP tool metadata exposed to Cursor agents."""

from __future__ import annotations

from typing import Any

_PROJECT_ROOT = {
    "type": "string",
    "description": (
        "Absolute path to the Cursor project root. Optional when the MCP server was started "
        "with --project-root, OBSIDIAN_CONTEXT_PROJECT_ROOT, or a single workspace root."
    ),
}

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "config_get_project",
        "description": (
            "Inspect how this Cursor project is linked to Obsidian documentation. "
            "Returns projectRoot, vaultPath, configured flag, index stats, and setupHint when vault is missing. "
            "Call this first in a new session before docs_search or docs_get_context_pack."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"projectRoot": _PROJECT_ROOT},
            "additionalProperties": False,
        },
    },
    {
        "name": "config_set_vault_path",
        "description": (
            "Bind an external Obsidian vault (folder of .md notes) to a Cursor project. "
            "Required once per project before search, context packs, or note edits work. "
            "Prefer the desktop GUI for folder picking; use this tool for scripted setup. "
            "After saving, run docs_reindex with mode=full."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": {
                    **_PROJECT_ROOT,
                    "description": "Absolute path to the Cursor project root to configure.",
                },
                "vaultPath": {
                    "type": "string",
                    "description": "Absolute path to the Obsidian vault or docs folder containing markdown files.",
                },
                "writeAccess": {
                    "type": "boolean",
                    "description": "Allow agents to create/patch/delete notes via MCP. Default false (read-only).",
                },
                "include": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns of files to index, e.g. ['**/*.md'].",
                },
                "exclude": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Glob patterns to skip, e.g. ['.obsidian/**', '.git/**'].",
                },
            },
            "required": ["projectRoot", "vaultPath"],
            "additionalProperties": False,
        },
    },
    {
        "name": "config_open_gui",
        "description": (
            "Request the Obsidian Context desktop app to open for visual setup "
            "(project root, vault folder, indexing, settings). "
            "Does not launch Electron by itself — user must run pnpm dev:desktop or the packaged app. "
            "Writes open-request.json consumed by the GUI on startup."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"projectRoot": _PROJECT_ROOT},
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_get_context_pack",
        "description": (
            "Primary agent tool: build a task-focused documentation bundle from the indexed Obsidian vault. "
            "Combines hybrid search, linked notes, and frontmatter within a token budget. "
            "Use before implementing features, debugging, or answering questions about project docs. "
            "Requires vault configured and index built (docs_reindex)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "task": {
                    "type": "string",
                    "description": "Natural-language description of what the agent needs to accomplish.",
                },
                "tokenBudget": {
                    "type": "integer",
                    "description": "Approximate max tokens for returned context. Default 6000.",
                },
                "topK": {
                    "type": "integer",
                    "description": "Number of search hits to consider. Default 12.",
                },
                "includeLinked": {
                    "type": "boolean",
                    "description": "Follow wikilinks from top hits. Default true.",
                },
                "includeFrontmatter": {
                    "type": "boolean",
                    "description": "Include YAML frontmatter in snippets. Default true.",
                },
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_search",
        "description": (
            "Search indexed Obsidian markdown: hybrid (default), semantic-only, or lexical-only. "
            "Returns ranked chunks with path, heading, score, and excerpt. "
            "Use docs_get_context_pack for broader agent context; use this for targeted lookups."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "query": {
                    "type": "string",
                    "description": "Search query (keywords or short question).",
                },
                "topK": {
                    "type": "integer",
                    "description": "Maximum number of results. Default 10.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["hybrid", "semantic", "lexical"],
                    "description": "hybrid = embeddings + FTS; semantic = vectors only; lexical = keyword FTS only.",
                },
                "filters": {
                    "type": "object",
                    "description": "Optional metadata filters (tags, paths) supported by the retriever.",
                },
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_read_note",
        "description": (
            "Read full markdown content of one note by vault-relative path. "
            "Returns content, frontmatter, headings, and sha256 hash. "
            "Always read before docs_patch_note and pass expectedSha256 to prevent lost updates."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "relativePath": {
                    "type": "string",
                    "description": "Path to the .md file relative to the vault root, e.g. 'Architecture/API.md'.",
                },
            },
            "required": ["relativePath"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_list_notes",
        "description": (
            "Browse indexed notes: optional text query, tag filter, and limit. "
            "Useful to discover filenames before docs_read_note or to audit vault coverage."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "query": {
                    "type": "string",
                    "description": "Optional substring filter on title or path.",
                },
                "tag": {
                    "type": "string",
                    "description": "Optional frontmatter/tag filter.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max notes to return. Default 50.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_reindex",
        "description": (
            "Build or refresh the local search index (SQLite FTS + vector embeddings). "
            "Run mode=full after vault setup or major vault changes; incremental for routine updates. "
            "First run may take ~30s while the embedding model downloads."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "mode": {
                    "type": "string",
                    "enum": ["incremental", "full"],
                    "description": "full = rebuild from scratch; incremental = changed files only.",
                },
                "force": {
                    "type": "boolean",
                    "description": "Reserved for future use; currently ignored.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_index_status",
        "description": (
            "Check whether the vault is configured and if an indexing job is running or complete. "
            "Poll after docs_reindex to wait for embeddings to finish."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"projectRoot": _PROJECT_ROOT},
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_patch_note",
        "description": (
            "Edit an existing note safely. Requires writeAccess enabled in project config. "
            "Modes: replace_exact, unified_diff, append_section, upsert_section. "
            "Workflow: docs_read_note → compute patch → docs_patch_note with expectedSha256 from read."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "relativePath": {
                    "type": "string",
                    "description": "Vault-relative path to the note to edit.",
                },
                "expectedSha256": {
                    "type": "string",
                    "description": "sha256 from the last docs_read_note; rejects stale concurrent edits.",
                },
                "mode": {
                    "type": "string",
                    "description": "Patch strategy: replace_exact | unified_diff | append_section | upsert_section.",
                },
                "patch": {
                    "type": "object",
                    "description": "Mode-specific payload (content, diff, section heading, etc.).",
                },
                "dryRun": {
                    "type": "boolean",
                    "description": "If true, validate patch without writing.",
                },
                "createBackup": {
                    "type": "boolean",
                    "description": "Create timestamped backup before write. Default true.",
                },
            },
            "required": ["relativePath", "expectedSha256", "mode", "patch"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_create_note",
        "description": (
            "Create a new markdown file in the vault. Requires writeAccess. "
            "Fails if the file exists unless overwrite=true. Triggers reindex of the new file."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "relativePath": {
                    "type": "string",
                    "description": "Vault-relative path for the new .md file.",
                },
                "content": {
                    "type": "string",
                    "description": "Full markdown body for the new note.",
                },
                "overwrite": {
                    "type": "boolean",
                    "description": "Replace existing file if present. Default false.",
                },
                "createBackup": {
                    "type": "boolean",
                    "description": "Backup existing file when overwriting. Default true.",
                },
            },
            "required": ["relativePath", "content"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_delete_note",
        "description": (
            "Delete a note from the vault. Requires writeAccess. "
            "Pass expectedSha256 from docs_read_note. Creates backup by default."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "relativePath": {
                    "type": "string",
                    "description": "Vault-relative path of the note to delete.",
                },
                "expectedSha256": {
                    "type": "string",
                    "description": "sha256 from docs_read_note for optimistic locking.",
                },
                "createBackup": {
                    "type": "boolean",
                    "description": "Save backup before deletion. Default true.",
                },
            },
            "required": ["relativePath", "expectedSha256"],
            "additionalProperties": False,
        },
    },
    {
        "name": "docs_rename_note",
        "description": (
            "Move/rename a note within the vault. Requires writeAccess and expectedSha256. "
            "Optional updateWikilinks adjusts [[wikilink]] references across the vault."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "projectRoot": _PROJECT_ROOT,
                "fromRelativePath": {
                    "type": "string",
                    "description": "Current vault-relative path.",
                },
                "toRelativePath": {
                    "type": "string",
                    "description": "New vault-relative path.",
                },
                "expectedSha256": {
                    "type": "string",
                    "description": "sha256 of the source file from docs_read_note.",
                },
                "updateWikilinks": {
                    "type": "boolean",
                    "description": "Rewrite wikilinks pointing to the old path. Default false.",
                },
            },
            "required": ["fromRelativePath", "toRelativePath", "expectedSha256"],
            "additionalProperties": False,
        },
    },
    {
        "name": "diagnostics_run",
        "description": (
            "Run a health checklist: project root, vault config, app data paths, SQLite, MCP launcher. "
            "Use when tools fail unexpectedly or after first-time setup to verify prerequisites."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"projectRoot": _PROJECT_ROOT},
            "additionalProperties": False,
        },
    },
]
