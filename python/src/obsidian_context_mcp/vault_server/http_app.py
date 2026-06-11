"""Starlette HTTP app: MCP (SSE) + admin REST."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from obsidian_context_mcp.core.vault_context import VaultContext
from obsidian_context_mcp.vault_server.admin_api import AdminApi
from obsidian_context_mcp.vault_server.auth import (
    parse_bearer_token,
    require_vault_context,
    reset_vault_context,
    resolve_scope_from_token,
    set_vault_context,
)
from obsidian_context_mcp.vault_server.tool_definitions import VAULT_TOOL_DEFINITIONS
from obsidian_context_mcp.vault_server.vault_tools import VAULT_TOOL_HANDLERS

_mcp_server = Server("obsidian-context-vault")


def _run_tool_handler(handler: Callable[..., Awaitable[Any]], args: dict[str, Any]) -> Any:
    return asyncio.run(handler(args))


@_mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(name=spec["name"], description=spec["description"], inputSchema=spec["inputSchema"])
        for spec in VAULT_TOOL_DEFINITIONS
    ]


@_mcp_server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
    args = arguments or {}
    handler = VAULT_TOOL_HANDLERS.get(name)
    if not handler:
        return [TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))]
    try:
        require_vault_context()
        result = await asyncio.to_thread(_run_tool_handler, handler, args)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    except Exception as exc:
        return [TextContent(type="text", text=json.dumps({"error": str(exc)}))]


def create_http_app(
    vault_ctx: VaultContext,
    *,
    on_startup: Callable[[], None] | None = None,
    on_shutdown: Callable[[], None] | None = None,
) -> Starlette:
    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        if on_startup is not None:
            on_startup()
        yield
        if on_shutdown is not None:
            on_shutdown()

    admin = AdminApi(vault_ctx)
    sse = SseServerTransport("/messages/")

    async def handle_sse(request: Request) -> Response:
        token = parse_bearer_token(request.headers.get("authorization"))
        scope = resolve_scope_from_token(vault_ctx, token)
        if scope is None:
            return JSONResponse({"error": "Invalid or missing scope token"}, status_code=401)

        scoped_ctx = VaultContext(
            vault_id=vault_ctx.vault_id,
            vault_path=vault_ctx.vault_path,
            vault_real_path=vault_ctx.vault_real_path,
            data_dir=vault_ctx.data_dir,
            config=vault_ctx.config,
            config_store=vault_ctx.config_store,
            scope_store=vault_ctx.scope_store,
            scope=scope,
        )
        auth_token = set_vault_context(scoped_ctx)
        try:
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:  # noqa: SLF001
                await _mcp_server.run(
                    streams[0],
                    streams[1],
                    _mcp_server.create_initialization_options(),
                )
        finally:
            reset_vault_context(auth_token)
        return Response()

    async def authenticated_messages(scope, receive, send):  # type: ignore[no-untyped-def]
        request = Request(scope, receive)
        token = parse_bearer_token(request.headers.get("authorization"))
        if resolve_scope_from_token(vault_ctx, token) is None:
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        await sse.handle_post_message(scope, receive, send)

    routes = [
        Route("/health", admin.health, methods=["GET"]),
        Route("/api/v1/status", admin.status, methods=["GET"]),
        Route("/api/v1/search", admin.search, methods=["POST"]),
        Route("/api/v1/reindex", admin.reindex, methods=["POST"]),
        Route("/api/v1/index-file", admin.index_file, methods=["POST"]),
        Route("/api/v1/scopes", admin.list_scopes, methods=["GET"]),
        Route("/api/v1/scopes", admin.upsert_scope, methods=["POST"]),
        Route("/api/v1/scopes/preview", admin.scope_preview, methods=["POST"]),
        Route("/api/v1/scopes/{scope_id}", admin.delete_scope, methods=["DELETE"]),
        Route("/api/v1/scopes/{scope_id}/regenerate-token", admin.regenerate_token, methods=["POST"]),
        Route("/api/v1/scopes/{scope_id}/cursor-config", admin.cursor_config, methods=["GET"]),
        Route("/api/v1/diagnostics", admin.diagnostics, methods=["GET"]),
        Route("/api/v1/config", admin.get_config, methods=["GET"]),
        Route("/api/v1/config", admin.update_config, methods=["PUT"]),
        Route("/sse", handle_sse, methods=["GET"]),
        Mount("/messages/", app=authenticated_messages),
    ]
    return Starlette(routes=routes, lifespan=lifespan)
