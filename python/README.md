# obsidian-context-mcp (Python)

Python core, MCP server, and GUI backend for Obsidian Context MCP.

## Development

```bash
uv sync --all-extras
uv run obsidian-context-mcp --help
uv run pytest tests/ -v
```

## CLI

```bash
uv run obsidian-context-mcp server
uv run obsidian-context-mcp server --project-root /path/to/project
uv run obsidian-context-mcp gui-backend --project-root /path/to/project
uv run obsidian-context-mcp index --project-root /path/to/project --mode incremental
uv run obsidian-context-mcp doctor --project-root /path/to/project
```
