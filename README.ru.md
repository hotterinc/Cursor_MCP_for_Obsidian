# obsidian-context-mcp

Локальный MCP-сервер для **Cursor**, который связывает текущий проект с внешним **Obsidian Vault**.  
Сервер индексирует Markdown-файлы, строит локальную векторную базу, предоставляет контекст агентам Cursor и поддерживает безопасное редактирование `.md`.

По умолчанию проект работает полностью локально: без облачных API и без отправки содержимого документов наружу.

## Архитектура

- **Python core**: конфиг, безопасность, индексация, поиск, редактирование, watcher
- **MCP server**: stdio-процесс для Cursor (`obsidian-context-mcp server`)
- **GUI backend**: JSON-RPC over stdio sidecar для Electron
- **Electron desktop**: UI, native folder picker, tray, lifecycle

## Быстрый старт (dev)

Требования:
- Node.js 20+, pnpm 9+
- Python 3.11+
- `uv` (или `python -m pip install uv`)

Установка:

```bash
git clone <repo>
cd obsidian-context-mcp

cd python
python -m uv sync --all-extras

cd ..
pnpm install
```

Запуск desktop GUI:

```bash
pnpm dev:desktop
```

Запуск MCP server:

```bash
cd python
python -m uv run obsidian-context-mcp server --project-root /absolute/path/to/project
```

## Конфигурация Cursor MCP

Пример (dev):

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
        "server",
        "--project-root",
        "G:/absolute/path/to/current/project"
      ]
    }
  }
}
```

## Как работать

1. В GUI выберите root проекта Cursor
2. Выберите папку Obsidian (внешнюю относительно репозитория)
3. Сохраните конфигурацию (хранится в app data, не в git)
4. Постройте индекс (full или incremental)
5. В агенте используйте `docs_get_context_pack` перед реализацией

## Основные MCP tools

- `config_get_project`
- `config_set_vault_path`
- `docs_reindex`
- `docs_index_status`
- `docs_search`
- `docs_get_context_pack`
- `docs_read_note`
- `docs_patch_note`
- `docs_create_note`
- `docs_delete_note`
- `docs_rename_note`
- `diagnostics_run`

## Безопасность

- Чтение/запись только `.md` внутри настроенного vault
- Защита от path traversal и symlink escape
- Запись в `.obsidian/**`, `.git/**`, `node_modules/**` запрещена
- Запись по умолчанию выключена (`writeAccess=false`)
- Для редактирования обязателен `expectedSha256`
- Перед destructive-операциями создаются backup-файлы (если не отключено)
- stdout MCP-процесса — только JSON-RPC сообщения, логи идут в stderr/файлы

## Где лежат данные

Через `platformdirs`:

```text
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

## Проверки

Python:

```bash
cd python
python -m uv run pytest tests -q
python -m uv run ruff check src tests
python -m uv run mypy src
```

Desktop:

```bash
pnpm --filter @obsidian-context/desktop typecheck
pnpm --filter @obsidian-context/desktop lint
```

## Лицензия

MIT, см. `LICENSE`.

