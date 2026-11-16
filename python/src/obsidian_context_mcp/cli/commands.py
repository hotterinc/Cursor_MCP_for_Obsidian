"""CLI command implementations."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from obsidian_context_mcp.shared.constants import DEFAULT_VAULT_SERVER_PORT

# Heavy modules (indexer, Chroma, embeddings) are imported inside the commands that
# need them, so the stdio proxy started by Claude Desktop stays small.
if TYPE_CHECKING:
    from obsidian_context_mcp.core.project import ProjectContext

SCOPE_TOKEN_ENV = "OBSIDIAN_CONTEXT_SCOPE_TOKEN"


def _require_ctx(project_root: str | None) -> ProjectContext:
    from obsidian_context_mcp.core.project import detect_project_context

    ctx = detect_project_context(cli_root=project_root)
    if ctx is None:
        typer.echo("Error: could not detect project root", err=True)
        raise typer.Exit(1)
    return ctx


def server(project_root: str | None = typer.Option(None, "--project-root")) -> None:
    from obsidian_context_mcp.core.logging import setup_logging
    from obsidian_context_mcp.core.ml_runtime import configure_ml_runtime
    from obsidian_context_mcp.mcp_server.server import run_mcp_server

    configure_ml_runtime()
    setup_logging(level="INFO")
    asyncio.run(run_mcp_server(project_root))


def vault_server(
    vault_path: str = typer.Option(..., "--vault-path"),
    data_dir: str = typer.Option(..., "--data-dir"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(DEFAULT_VAULT_SERVER_PORT, "--port"),
) -> None:
    from obsidian_context_mcp.core.ml_runtime import configure_ml_runtime
    from obsidian_context_mcp.vault_server.server import run_vault_server

    configure_ml_runtime()
    run_vault_server(vault_path, data_dir, host=host, port=port)


def _runtime_port(data_dir: str) -> int:
    runtime = Path(data_dir) / "runtime.json"
    try:
        return int(json.loads(runtime.read_text(encoding="utf-8"))["port"])
    except (OSError, ValueError, KeyError) as exc:
        raise RuntimeError(
            f"vault-server is not running for {data_dir} (no {runtime.name}); open Obsidian first"
        ) from exc


def cursor_proxy(
    port: int | None = typer.Option(None, "--port", help="vault-server port"),
    data_dir: str | None = typer.Option(
        None, "--data-dir", help="Plugin data dir; the current port is read from runtime.json"
    ),
    host: str = typer.Option("127.0.0.1", "--host"),
    token: str | None = typer.Option(None, "--token"),
    token_env: str = typer.Option(SCOPE_TOKEN_ENV, "--token-env"),
) -> None:
    """Expose the vault server as a stdio MCP server (Claude Desktop, older Cursor)."""
    from obsidian_context_mcp.mcp_server.proxy import run_stdio_proxy

    credential = token or os.environ.get(token_env)
    if not credential:
        typer.echo(f"Set {token_env} or pass --token", err=True)
        raise typer.Exit(2)
    try:
        if port is None:
            if data_dir is None:
                typer.echo("Pass --port or --data-dir", err=True)
                raise typer.Exit(2)
            port = _runtime_port(data_dir)
        asyncio.run(run_stdio_proxy(f"http://{host}:{port}/sse", credential))
    except typer.Exit:
        raise
    except Exception as exc:
        typer.echo(f"MCP proxy failed: {exc}", err=True)
        raise typer.Exit(1) from exc


def gui_backend(project_root: str = typer.Option(..., "--project-root")) -> None:
    from obsidian_context_mcp.core.logging import setup_logging
    from obsidian_context_mcp.core.ml_runtime import configure_ml_runtime
    from obsidian_context_mcp.gui_backend.server import run_gui_backend

    configure_ml_runtime()
    setup_logging(level="INFO")
    run_gui_backend(project_root)


def index_cmd(
    project_root: str = typer.Option(..., "--project-root"),
    mode: str = typer.Option("incremental", "--mode"),
) -> None:
    from obsidian_context_mcp.core.indexer import Indexer
    from obsidian_context_mcp.core.logging import setup_logging
    from obsidian_context_mcp.shared.types import IndexMode

    setup_logging(level="INFO")
    ctx = _require_ctx(project_root)
    indexer = Indexer(ctx)
    index_mode = IndexMode.FULL if mode == "full" else IndexMode.INCREMENTAL
    progress = indexer.run(index_mode)
    typer.echo(json.dumps(progress.model_dump(), indent=2))


def doctor(project_root: str = typer.Option(..., "--project-root")) -> None:
    from obsidian_context_mcp.core.diagnostics import run_diagnostics_for_root
    from obsidian_context_mcp.core.logging import setup_logging

    setup_logging(level="INFO")
    checks = run_diagnostics_for_root(project_root)
    typer.echo(json.dumps([c.model_dump() for c in checks], indent=2))


def config_show(project_root: str = typer.Option(..., "--project-root")) -> None:
    ctx = _require_ctx(project_root)
    config = ctx.config_store.load()
    typer.echo(json.dumps(config.model_dump() if config else {}, indent=2))


def config_set_vault(
    project_root: str = typer.Option(..., "--project-root"),
    vault_path: str = typer.Option(..., "--vault-path"),
) -> None:
    from obsidian_context_mcp.core.vault import validate_vault_path

    ctx = _require_ctx(project_root)
    validation = validate_vault_path(vault_path)
    config = ctx.config_store.create_or_update(
        project_root,
        vault_path=validation.vault_path,
    )
    typer.echo(json.dumps(config.model_dump(), indent=2))
