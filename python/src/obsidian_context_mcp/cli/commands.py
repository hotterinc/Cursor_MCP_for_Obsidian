"""CLI command implementations."""

from __future__ import annotations

import asyncio
import json

import typer

from obsidian_context_mcp.core.diagnostics import run_diagnostics_for_root
from obsidian_context_mcp.core.indexer import Indexer
from obsidian_context_mcp.core.logging import setup_logging
from obsidian_context_mcp.core.project import detect_project_context
from obsidian_context_mcp.core.vault import validate_vault_path
from obsidian_context_mcp.gui_backend.server import run_gui_backend
from obsidian_context_mcp.mcp_server.server import run_mcp_server
from obsidian_context_mcp.shared.types import IndexMode


def _require_ctx(project_root: str | None):
    ctx = detect_project_context(cli_root=project_root)
    if ctx is None:
        typer.echo("Error: could not detect project root", err=True)
        raise typer.Exit(1)
    return ctx


def server(project_root: str = typer.Option(..., "--project-root")) -> None:
    setup_logging(level="INFO")
    asyncio.run(run_mcp_server(project_root))


def gui_backend(project_root: str = typer.Option(..., "--project-root")) -> None:
    setup_logging(level="INFO")
    run_gui_backend(project_root)


def index_cmd(
    project_root: str = typer.Option(..., "--project-root"),
    mode: str = typer.Option("incremental", "--mode"),
) -> None:
    setup_logging(level="INFO")
    ctx = _require_ctx(project_root)
    indexer = Indexer(ctx)
    index_mode = IndexMode.FULL if mode == "full" else IndexMode.INCREMENTAL
    progress = indexer.run(index_mode)
    typer.echo(json.dumps(progress.model_dump(), indent=2))


def doctor(project_root: str = typer.Option(..., "--project-root")) -> None:
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
    ctx = _require_ctx(project_root)
    validation = validate_vault_path(vault_path)
    config = ctx.config_store.create_or_update(
        project_root,
        vault_path=validation.vault_path,
    )
    typer.echo(json.dumps(config.model_dump(), indent=2))
