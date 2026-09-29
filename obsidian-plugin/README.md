# Obsidian Context MCP Plugin

Community plugin that hosts the vector index and MCP server inside Obsidian.

## Install (development)

1. Install Python package: `cd ../python && pip install -e .`
2. Build plugin: `npm install && npm run build`
3. Copy to vault: `.obsidian/plugins/obsidian-context-mcp/` (`manifest.json`, `main.js`, `styles.css`)
4. Enable in Obsidian → Community plugins

## Usage

- **Semantic search vault** — command palette
- **Manage Cursor and Codex access scopes** — limit which folders Cursor can access via MCP
- **Copy Cursor JSON** — paste into Cursor MCP settings (`/sse` URL + Authorization header)
- **Copy Codex config** — paste TOML into Codex configuration and set `OBSIDIAN_CONTEXT_SCOPE_TOKEN` from **Copy scope token**

Data directory: `.obsidian/plugins/obsidian-context-mcp/data/`
