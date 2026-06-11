# obsidian-context-mcp

Локальный MCP-сервер для **Cursor**, который связывает текущий проект с внешним **Obsidian Vault**.  
Сервер индексирует Markdown-файлы, строит локальную векторную базу, предоставляет контекст агентам Cursor и поддерживает безопасное редактирование `.md`.

По умолчанию проект работает полностью локально: без облачных API и без отправки содержимого документов наружу.

## Архитектура

**Рекомендуемый режим (Obsidian-hosted):**

- **Obsidian plugin** — запускает `vault-server`, semantic search в vault, управление Access Scopes
- **Python vault-server** — HTTP MCP (SSE) + admin REST, один индекс на vault (SQLite + Chroma)
- **Cursor** — подключается по URL + Bearer token scope (не запускает Python)

```
Obsidian Plugin ──spawn──► vault-server ──► SQLite + Chroma (per vault)
Cursor Agent ──HTTP/SSE + scope token──► vault-server
```

**Legacy (deprecated):**

- **MCP server (stdio)** — Cursor сам запускает `obsidian-context-mcp server`
- **GUI backend + Electron desktop** — fallback без Obsidian plugin

## Быстрый старт (Obsidian plugin)

1. Установите Python-пакет:

```bash
cd python && uv sync --all-extras
pip install -e .   # или uv pip install -e .
```

2. Соберите plugin и скопируйте в vault:

```bash
cd obsidian-plugin
npm install && npm run build
cp -r manifest.json main.js styles.css /path/to/vault/.obsidian/plugins/obsidian-context-mcp/
```

3. В Obsidian: Settings → Community plugins → включите **Obsidian Context MCP**
4. Plugin автоматически стартует `vault-server` и incremental index
5. Settings plugin → **Access scopes** → создайте scope с папкой `Projects/MyApp/**`
6. **Copy JSON** → вставьте в Cursor MCP settings

## Конфигурация Cursor MCP (рекомендуется)

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

URL и token берутся из plugin → Access scopes → Copy JSON (порт в `runtime.json`).

Первый tool в сессии: `scope_get_info`, затем `docs_get_context_pack` / `docs_search`.

## Access Scopes

Vault индексируется целиком, но Cursor видит только разрешённые папки:

- каждый scope: `include` / `exclude` globs + bearer token
- `writeAccess=false` по умолчанию
- `canReindex=false` по умолчанию для Cursor scopes

Данные scope: `.obsidian/plugins/obsidian-context-mcp/data/scopes.json`

## vault-server (вручную)

```bash
obsidian-context-mcp vault-server \
  --vault-path /path/to/vault \
  --data-dir /path/to/vault/.obsidian/plugins/obsidian-context-mcp/data \
  --host 127.0.0.1 \
  --port 0
```

## Legacy: stdio MCP (deprecated)

<details>
<summary>Старый режим — Cursor запускает MCP сам</summary>

- **Python core**: конфиг, безопасность, индексация, поиск, редактирование, watcher
- **MCP server**: stdio-процесс для Cursor (`obsidian-context-mcp server`)
- **GUI backend**: JSON-RPC over stdio sidecar для Electron
- **Electron desktop**: UI, native folder picker, tray, lifecycle

</details>

## Быстрый старт (dev, legacy)

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

Запуск MCP server (одной командой, без привязки к одному проекту):

```bash
pnpm mcp:start
```

Альтернатива напрямую:

```bash
cd python
python -m uv run obsidian-context-mcp server
```

## Конфигурация Cursor MCP (legacy stdio)

> **Deprecated.** Используйте Obsidian plugin + URL config (см. выше).

Пример (dev, мультипроектный режим):

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

Если нужно зафиксировать один проект, добавьте `--project-root`.

## Как работать

1. В GUI выберите root проекта Cursor
2. Выберите папку Obsidian (внешнюю относительно репозитория)
3. Сохраните конфигурацию (хранится в app data, не в git)
4. Постройте индекс (full или incremental)
5. В агенте используйте `docs_get_context_pack` перед реализацией

Для одновременной работы с несколькими проектами:
- сервер запускается один раз (`pnpm mcp:start`)
- в каждом tool можно передавать `projectRoot` целевого проекта
- если `projectRoot` не передан, используется автоопределение (env/cwd/last active)

### Как конкретизировать путь к проекту

Есть 3 способа:

1. На уровне запуска сервера:

```bash
python -m uv run obsidian-context-mcp server --project-root G:/work/project-a
```

2. Через переменную окружения:

```bash
set OBSIDIAN_CONTEXT_PROJECT_ROOT=G:/work/project-a
pnpm mcp:start
```

3. В каждом вызове tool (рекомендуется для мультипроекта):

```json
{
  "projectRoot": "G:/work/project-b",
  "query": "архитектура аутентификации",
  "topK": 10,
  "mode": "hybrid"
}
```

Приоритет определения `projectRoot`: `--project-root` → `OBSIDIAN_CONTEXT_PROJECT_ROOT` → roots клиента → cwd → last active project.

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

**Vault-centric (plugin):**

```text
<vault>/.obsidian/plugins/obsidian-context-mcp/data/
  vault.json
  scopes.json
  runtime.json
  index/
    db.sqlite
    chroma/
```

**Legacy (project-centric, app data):**

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

