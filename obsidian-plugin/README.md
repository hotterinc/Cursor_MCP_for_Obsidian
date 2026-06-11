# Obsidian Context MCP Plugin

Community plugin that hosts the vector index and MCP server inside Obsidian.

## Install (development)

1. Install Python package: `cd ../python && pip install -e .`
2. Build plugin: `npm install && npm run build`
3. Copy to vault: `.obsidian/plugins/obsidian-context-mcp/` (`manifest.json`, `main.js`, `styles.css`)
4. Enable in Obsidian → Community plugins

## Usage

- **Semantic search vault** — command palette
- **Manage Cursor access scopes** — limit which folders Cursor can access via MCP
- **Copy JSON** — paste into Cursor MCP settings (`url` + `Authorization` header)

Data directory: `.obsidian/plugins/obsidian-context-mcp/data/`
