"""CLI entry point."""

from __future__ import annotations

import typer

from obsidian_context_mcp.cli import commands

app = typer.Typer(name="obsidian-context-mcp", no_args_is_help=True)

app.command("server")(commands.server)
app.command("gui-backend")(commands.gui_backend)
app.command("index")(commands.index_cmd)
app.command("doctor")(commands.doctor)

config_app = typer.Typer(name="config", no_args_is_help=True)
config_app.command("show")(commands.config_show)
config_app.command("set-vault")(commands.config_set_vault)
app.add_typer(config_app, name="config")
