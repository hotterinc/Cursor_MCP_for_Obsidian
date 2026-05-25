"""System diagnostics."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from obsidian_context_mcp.core.app_paths import get_app_data_dir, get_project_db_path
from obsidian_context_mcp.core.embeddings import create_embedding_provider
from obsidian_context_mcp.core.project import ProjectContext, detect_project_context
from obsidian_context_mcp.core.security import SecurityBoundary
from obsidian_context_mcp.core.sqlite_store import SQLiteStore
from obsidian_context_mcp.core.vault import validate_vault_path
from obsidian_context_mcp.core.vector_store import create_vector_store
from obsidian_context_mcp.shared.types import DiagnosticCheck, DiagnosticStatus


def _check(name: str, ok: bool, message: str, *, warn: bool = False, details: dict | None = None) -> DiagnosticCheck:
    if ok:
        status = DiagnosticStatus.PASS
    elif warn:
        status = DiagnosticStatus.WARN
    else:
        status = DiagnosticStatus.FAIL
    return DiagnosticCheck(name=name, status=status, message=message, details=details or {})


def run_diagnostics(ctx: ProjectContext) -> list[DiagnosticCheck]:
    checks: list[DiagnosticCheck] = []

    root_exists = Path(ctx.project_root).exists()
    checks.append(_check("project_root_exists", root_exists, f"Project root: {ctx.project_root}"))

    real_ok = bool(ctx.project_real_path)
    checks.append(_check("project_realpath", real_ok, f"Real path: {ctx.project_real_path}"))

    configured = ctx.config is not None and ctx.config.configured
    checks.append(
        _check("vault_configured", configured, "Vault path configured" if configured else "Vault not configured", warn=not configured)
    )

    if ctx.config and ctx.config.vault_path:
        vp = Path(ctx.config.vault_path)
        checks.append(_check("vault_exists", vp.exists(), f"Vault: {ctx.config.vault_path}"))
        checks.append(_check("vault_readable", os.access(ctx.config.vault_real_path or vp, os.R_OK), "Vault readable"))
        if ctx.config.write_access:
            checks.append(
                _check(
                    "vault_writable",
                    os.access(ctx.config.vault_real_path or vp, os.W_OK),
                    "Vault writable (write access enabled)",
                )
            )
        else:
            checks.append(
                DiagnosticCheck(
                    name="vault_writable",
                    status=DiagnosticStatus.SKIP,
                    message="Write access disabled",
                )
            )

        try:
            validation = validate_vault_path(
                ctx.config.vault_path,
                include=ctx.config.include,
                exclude=ctx.config.exclude,
                docs_subfolder=ctx.config.docs_subfolder,
            )
            checks.append(
                _check(
                    "vault_validation",
                    validation.can_read,
                    f"{validation.markdown_files_count} markdown files",
                    details={"warnings": validation.warnings},
                )
            )
        except Exception as exc:
            checks.append(_check("vault_validation", False, str(exc)))

        try:
            boundary = SecurityBoundary(ctx.config)
            boundary.assert_inside_vault(boundary.vault_real_path)
            checks.append(_check("symlink_escape", True, "Vault root passes security boundary"))
        except Exception as exc:
            checks.append(_check("symlink_escape", False, str(exc)))

    app_data = get_app_data_dir()
    checks.append(_check("app_data_writable", os.access(app_data, os.W_OK), f"App data: {app_data}"))

    try:
        db_path = get_project_db_path(ctx.project_id)
        store = SQLiteStore(db_path)
        store.initialize()
        checks.append(_check("sqlite_accessible", True, f"SQLite: {db_path}"))
        store.close()
    except Exception as exc:
        checks.append(_check("sqlite_accessible", False, str(exc)))

    if ctx.config and ctx.config.configured:
        try:
            vs = create_vector_store(ctx.project_id)
            healthy = vs.healthcheck(ctx.project_id)
            checks.append(_check("vector_store", healthy, "Vector store accessible"))
        except Exception as exc:
            checks.append(_check("vector_store", False, str(exc)))

        try:
            provider = create_embedding_provider(ctx.config, ctx.project_id)
            hc = provider.healthcheck()
            checks.append(
                _check(
                    "embedding_provider",
                    hc.ok,
                    hc.message,
                    warn=not hc.ok,
                    details={"provider": provider.name},
                )
            )
        except Exception as exc:
            checks.append(_check("embedding_provider", False, str(exc)))

    # MCP command available
    mcp_cmd = shutil.which("obsidian-context-mcp") or shutil.which("uv")
    checks.append(
        _check(
            "mcp_server_command",
            mcp_cmd is not None,
            f"MCP launcher: {mcp_cmd or 'not found'}",
            warn=mcp_cmd is None,
        )
    )

    checks.append(
        DiagnosticCheck(
            name="cursor_config_suggestion",
            status=DiagnosticStatus.PASS,
            message="Add obsidian-context MCP server to Cursor settings",
            details={
                "example": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        "<repo>/python",
                        "run",
                        "obsidian-context-mcp",
                        "server",
                        "--project-root",
                        ctx.project_root,
                    ],
                }
            },
        )
    )

    return checks


def run_diagnostics_for_root(project_root: str | None = None) -> list[DiagnosticCheck]:
    ctx = detect_project_context(cli_root=project_root)
    if ctx is None:
        return [
            DiagnosticCheck(
                name="project_detection",
                status=DiagnosticStatus.FAIL,
                message="Could not detect project root",
            )
        ]
    return run_diagnostics(ctx)
