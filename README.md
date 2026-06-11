# obsidian-context-mcp

Russian documentation: [`README.ru.md`](README.ru.md)

Local MCP server for **Cursor** that connects your Cursor project to an external **Obsidian** documentation vault. Indexes Markdown locally, builds a vector database, and gives Cursor agents searchable context plus safe editing of `.md` files.

Everything runs **locally**. No cloud APIs by default. User Markdown never leaves the machine.

## Architecture

**Recommended (Obsidian-hosted):**

- **Obsidian plugin** — starts `vault-server`, in-vault semantic search, Access Scope management
- **Python vault-server** — HTTP MCP (SSE) + admin REST, one index per vault (SQLite + Chroma)
- **Cursor** — connects via URL + Bearer scope token (does not spawn Python)

```
Obsidian Plugin ──spawn──► vault-server ──► SQLite + Chroma (per vault)
Cursor Agent ──HTTP/SSE + scope token──► vault-server
```

**Legacy (deprecated):**

- **MCP server (stdio)** — Cursor spawns `obsidian-context-mcp server`
- **GUI backend + Electron desktop** — fallback without Obsidian plugin

## Quick start (Obsidian plugin)

1. Install the Python package:

```bash
cd python && uv sync --all-extras
pip install -e .
```

2. Build the plugin and copy into your vault:

```bash
cd obsidian-plugin
npm install && npm run build
cp manifest.json main.js styles.css /path/to/vault/.obsidian/plugins/obsidian-context-mcp/
```

3. In Obsidian: enable **Obsidian Context MCP** under Community plugins
4. The plugin auto-starts `vault-server` and runs incremental indexing
5. Plugin settings → **Access scopes** → create a scope (e.g. `Projects/MyApp/**`)
6. **Copy JSON** → paste into Cursor MCP settings

## Cursor MCP configuration (recommended)

```json
{
  "mcpServers": {
    "obsidian-context": {
      "url": "http://127.0.0.1:18432/sse",
      "headers": {
        "Authorization": "Bearer ocm_..."
      }
    }
  }
}
```

Port and token come from the plugin (Access scopes → Copy JSON). First tool in a session: `scope_get_info`, then `docs_get_context_pack` / `docs_search`.

## Access Scopes

The full vault is indexed, but each Cursor connection only sees allowed folders via bearer tokens stored in `scopes.json`.

## vault-server (manual)

```bash
obsidian-context-mcp vault-server \
  --vault-path /path/to/vault \
  --data-dir /path/to/vault/.obsidian/plugins/obsidian-context-mcp/data
```

## Architecture (legacy)

<details>
<summary>Old stdio + Electron flow</summary>

- **Python core** — config, security, indexing, retrieval, editing, watcher
- **MCP server** — stdio process started by Cursor (`obsidian-context-mcp server`)
- **GUI backend** — JSON-RPC over stdio sidecar for Electron
- **Electron desktop** — folder pickers, tray, settings UI (no business logic)

```
Cursor Agent ──MCP stdio──► Python MCP Server ──┐
                                                  ├──► Python Core ──► SQLite + Chroma
Electron GUI ──IPC──► Main ──JSON-RPC stdio──► GUI Backend ──┘
                                                  └──► Obsidian vault (.md only)
```

</details>

App data (legacy project-centric index) lives in OS app data via `platformdirs`, **not** in your git repo.

## Installation (development, legacy)

### Prerequisites

- Node.js 20+, pnpm 9+
- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (or `pip install uv`)

### Setup

```bash
git clone <repo>
cd obsidian-context-mcp

# Python
cd python
uv sync --all-extras   # or: python -m uv sync --all-extras

# Node
cd ..
pnpm install
```

One-command MCP start:

```bash
pnpm mcp:start
```

## Cursor MCP configuration (legacy stdio)

> **Deprecated.** Use the Obsidian plugin + URL config (see above).

**Development (multi-project mode, recommended)**:

```json
{
  "mcpServers": {
    "obsidian-context": {
      "command": "uv",
      "args": [
        "--directory",
        "G:/absolute/path/to/obsidian-context-mcp/python",
        "run",
        "obsidian-context-mcp",
        "server"
      ]
    }
  }
}
```

**Installed CLI**:

```json
{
  "mcpServers": {
    "obsidian-context": {
      "command": "obsidian-context-mcp",
      "args": ["server", "--project-root", "G:/absolute/path/to/your/cursor/project"]
    }
  }
}
```

> Prefer **global/local** Cursor MCP config over committing `.cursor/mcp.json` — project-level config may accidentally commit private vault paths.

If you want to pin a single project, keep `--project-root`.

## Desktop GUI

```bash
pnpm dev:desktop
```

Or with project root:

```bash
pnpm dev:desktop -- --project-root G:/path/to/project
```

### Workflow

1. **Choose project root** — your Cursor workspace folder
2. **Choose Obsidian folder** — external vault or docs folder (native folder picker)
3. **Save configuration** — binding stored in app data
4. **Build index** — full or incremental
5. Use MCP tools from Cursor agents

For multiple projects at the same time:
- run one shared MCP server (`pnpm mcp:start`)
- pass `projectRoot` in tool input when you need a specific project
- when omitted, the server falls back to auto-detection (env/cwd/last active)

### How to pin project path

You can set `projectRoot` in 3 ways:

1. At server startup:

```bash
python -m uv run obsidian-context-mcp server --project-root G:/work/project-a
```

2. Via environment variable:

```bash
set OBSIDIAN_CONTEXT_PROJECT_ROOT=G:/work/project-a
pnpm mcp:start
```

3. Per tool call (recommended for multi-project):

```json
{
  "projectRoot": "G:/work/project-b",
  "query": "authentication architecture",
  "topK": 10,
  "mode": "hybrid"
}
```

Resolution priority is: `--project-root` → `OBSIDIAN_CONTEXT_PROJECT_ROOT` → client workspace roots → cwd → last active project.

## MCP tools (highlights)

| Tool | Purpose |
|------|---------|
| `docs_get_context_pack` | Primary tool — task-oriented doc context for agents |
| `docs_search` | Hybrid semantic + lexical search |
| `docs_read_note` | Read note + `sha256` for safe edits |
| `docs_patch_note` | Edit with `expectedSha256` + backup |
| `config_get_project` | Project / vault status |
| `config_open_gui` | Open desktop app |
| `diagnostics_run` | Health checklist |

### Agent workflow

Before coding, agents should call **`docs_get_context_pack`** with the current task.

When editing docs:

1. `docs_read_note` → get `sha256`
2. `docs_patch_note` with `expectedSha256` (write access must be enabled in GUI)

## Indexing

```bash
cd python
uv run obsidian-context-mcp index --project-root /path/to/project --mode full
uv run obsidian-context-mcp index --project-root /path/to/project --mode incremental
```

External Obsidian edits are picked up by the **watchdog** watcher (when enabled).

## Data storage

```
appData/obsidian-context-mcp/
  config.json
  runtime/
  projects/<projectId>/
    project.json
    db.sqlite
    chroma/
    backups/
    logs/
```

`projectId = sha256(realpath(projectRoot))`

## Security model

- Read/write limited to configured vault `.md` files only
- Path traversal, symlink escape, `.obsidian/**` writes blocked
- **Write access off by default** — enable in GUI
- All writes require **`expectedSha256`**
- Backups before destructive ops (configurable)
- MCP stdout = protocol only; logs go to stderr + log files
- Electron renderer: sandbox, no Node integration

## Backups

Before patch/delete/rename:

```
appData/.../backups/YYYY-MM-DD/<timestamp>__<encodedPath>.md
```

## Reset / delete local index

Use **Settings → Reset index (full rebuild)** in the GUI, or delete:

```
appData/obsidian-context-mcp/projects/<projectId>/
```

## Build & package

```bash
pnpm python:test
pnpm build:desktop
./scripts/build-python.sh      # PyInstaller sidecar
./scripts/package-desktop.sh   # electron-builder
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| MCP not connecting | Check `uv run obsidian-context-mcp server --project-root ...` manually |
| Empty search results | Run full index; check vault path in GUI |
| Write rejected | Enable write access; pass correct `expectedSha256` |
| Model download | First run downloads `intfloat/multilingual-e5-small` locally — allow network once |
| Dirty MCP stdout | Ensure no print/logging to stdout in server process |

## CLI reference

```bash
uv run obsidian-context-mcp server --project-root <path>
uv run obsidian-context-mcp gui-backend --project-root <path>
uv run obsidian-context-mcp index --project-root <path> --mode incremental
uv run obsidian-context-mcp doctor --project-root <path>
uv run obsidian-context-mcp config show --project-root <path>
uv run obsidian-context-mcp config set-vault --project-root <path> --vault-path <path>
```

## License

MIT — see [LICENSE](LICENSE).
