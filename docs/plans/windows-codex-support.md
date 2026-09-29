# Windows reliability and Codex MCP implementation plan

Goal: Fix the defects documented in TECHNICAL_AUDIT.md and provide a local scoped MCP connection for Codex while retaining Cursor SSE.
Architecture: Existing Python core remains authoritative; Starlette gains authenticated stateless Streamable HTTP beside legacy SSE. Obsidian uses a separate local admin capability. No public hosting or ChatGPT connector is introduced.
Stack: Python 3.12, MCP SDK 1.x, Starlette, SQLite/Chroma, TypeScript, Electron, Obsidian, npm/pnpm, PyInstaller.
Spec: TECHNICAL_AUDIT.md, followed by the user request to implement its fixes and Codex first.

## Constraints
- Work in D:/ProjectsWH/Cursor_MCP_for_Obsidian, branch fix/windows-codex-support. Push only the working branch; do not merge main.
- Preserve core architecture and existing Cursor endpoint.
- Empty scope include means deny all; explicit **/*.md means full Markdown access. Explain this security correction for existing scopes.
- Admin bearer is separate from scope bearer; store it locally with runtime capability, never export it in MCP configuration or list scopes.
- MCP token is checked on every HTTP request and tool call. A session belongs to one scope token.
- Codex export uses /mcp and bearer_token_env_var = OBSIDIAN_CONTEXT_SCOPE_TOKEN; an explicit admin-only token copy action supplies the environment secret separately.
- Tool errors use isError; tools carry accurate read/write/destructive annotations.
- Build verification must validate real runtime imports and indexing, not merely health or exit zero.
- No changes to unrelated user files, no remote release or main writes, no model downloads during tests.

## Tasks
- [x] Python core: failing tests for scoped segment globs, empty scopes, index traversal/symlinks, scope-aware pagination, overwrite backup/hash and concurrent editor changes. Fix minimally and run Python tests, Ruff and mypy for owned files.
- [x] Packaging: tests for frozen CLI and native-command failures. Fix PyInstaller exclusions, dependency lock/build environment, platform launch commands, release provenance and fresh artifacts. Add CI checks and binary smoke verification.
- [x] Plugin and desktop: tests for parent/child scope selection and sidecar lifecycle; fix TypeScript errors, admin capability headers and token-preserving scope edits, Codex export UI, server identity, settings refresh, safe process ownership and Windows process behavior.
- [x] MCP transport: failing integration tests for Streamable HTTP initialize/list/call, SSE compatibility, missing/invalid credentials, admin isolation, cross-token sessions, permission updates and error flags. Implement transport lifespan/auth and exports; fix stdio CLI root.
- [x] Integration: run all Python/TS tests, Ruff/mypy, both builds; rebuild Windows binary and exercise imports, synthetic indexing and real MCP SDK clients. Inspect full diff.
- [x] Documentation: update English/Russian setup and release install docs with Codex local configuration, admin upgrade behavior, empty-scope semantics and verified limits. Mark audit findings addressed with evidence.

## Review focus
1. Existing installations missing admin capability must restart safely without trusting another vault/server.
2. Masked scope list updates must preserve token; stale UI updates must not revert a rotated token.
3. Windows process handling may terminate only a verified owned process, never an unrelated port listener.
4. Realpath checks must occur before all indexing reads including incremental unchanged files.
5. Concurrent scopes and long-running SSE sessions must never borrow another scope or retain revoked permissions.
