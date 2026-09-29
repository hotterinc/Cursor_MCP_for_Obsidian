"""Starlette HTTP app: MCP (SSE) + admin REST."""

from __future__ import annotations

import asyncio
import json
import re
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
from starlette.types import Receive, Scope, Send

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

_mcp_server = Server("obsidian-context-vault", instructions="Call scope_get_info first. Access only permitted vault notes. Use docs_get_context_pack for context. Read notes before editing and supply their sha256 to avoid overwriting concurrent changes.")


async def _await_handler(handler: Callable[..., Awaitable[Any]], args: dict[str, Any]) -> Any:
    return await handler(args)


def _run_tool_handler(handler: Callable[..., Awaitable[Any]], args: dict[str, Any]) -> Any:
    return asyncio.run(_await_handler(handler, args))


@_mcp_server.list_tools()  # type: ignore[no-untyped-call, untyped-decorator]
async def list_tools() -> list[Tool]:
    return [
        Tool(name=spec["name"], description=spec["description"], inputSchema=spec["inputSchema"], annotations=ToolAnnotations(readOnlyHint=spec["name"] not in {"docs_reindex", "docs_patch_note", "docs_create_note", "docs_delete_note", "docs_rename_note"}, openWorldHint=False))
        for spec in VAULT_TOOL_DEFINITIONS
    ]


@_mcp_server.call_tool()  # type: ignore[untyped-decorator]
async def call_tool(name: str, arguments: dict[str, Any] | None) -> CallToolResult:
    args = arguments or {}
    handler = VAULT_TOOL_HANDLERS.get(name)
    if not handler:
        return CallToolResult(isError=True, content=[TextContent(type="text", text=json.dumps({"error": f"unknown tool: {name}"}))])
    try:
        require_vault_context()
        result = await asyncio.to_thread(_run_tool_handler, handler, args)
        return CallToolResult(content=[TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))])
    except Exception as exc:
        return CallToolResult(isError=True, content=[TextContent(type="text", text=json.dumps({"error": str(exc)}))])


def create_http_app(
    vault_ctx: VaultContext,
    *,
    admin_token: str | None = None,
    on_startup: Callable[[], None] | None = None,
    on_shutdown: Callable[[], None] | None = None,
) -> Starlette:
    capability = admin_token or secrets.token_urlsafe(32)
    manager = StreamableHTTPSessionManager(_mcp_server, json_response=True, stateless=True)
    sessions: dict[str, str] = {}

    class AdminAuthorization:
        def __init__(self, app: Any) -> None:
            self.app = app

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            if scope["type"] == "http" and scope["path"].startswith("/api/v1/"):
                request = Request(scope, receive)
                credential = parse_bearer_token(request.headers.get("authorization"))
                if not credential or not secrets.compare_digest(credential, capability):
                    await JSONResponse({"error": "Unauthorized"}, status_code=401)(scope, receive, send)
                    return
            await self.app(scope, receive, send)

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        if on_startup is not None:
            on_startup()
        async with manager.run():
            try:
                yield
            finally:
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
        auth_token = set_vault_context(scoped_ctx, token)
        bound_sessions: list[str] = []

        async def bind_session(message: Any) -> None:
            if message["type"] == "http.response.body":
                body = message.get("body", b"").decode("utf-8", errors="replace")
                match = re.search(r"session_id=([0-9a-fA-F]{32})", body)
                if match and "event: endpoint" in body and token:
                    session_id = match.group(1).lower()
                    sessions[session_id] = token
                    bound_sessions.append(session_id)
            await request._send(message)

        try:
            async with sse.connect_sse(request.scope, request.receive, bind_session) as streams:  # noqa: SLF001
                await _mcp_server.run(
                    streams[0],
                    streams[1],
                    _mcp_server.create_initialization_options(),
                )
        finally:
            for session_id in bound_sessions:
                sessions.pop(session_id, None)
            reset_vault_context(auth_token)
        return Response()

    async def authenticated_messages(scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        token = parse_bearer_token(request.headers.get("authorization"))
        if resolve_scope_from_token(vault_ctx, token) is None:
            response = JSONResponse({"error": "Unauthorized"}, status_code=401)
            await response(scope, receive, send)
            return
        try:
            session_id = UUID(request.query_params.get("session_id", "")).hex
        except ValueError:
            await JSONResponse({"error": "Invalid session"}, status_code=400)(scope, receive, send)
            return
        owner = sessions.get(session_id)
        if owner is None or not token or not secrets.compare_digest(owner, token):
            await JSONResponse({"error": "Session token mismatch"}, status_code=403)(scope, receive, send)
            return
        await sse.handle_post_message(scope, receive, send)

    async def streamable_http(scope: Scope, receive: Receive, send: Send) -> None:
        request = Request(scope, receive)
        token = parse_bearer_token(request.headers.get("authorization"))
        if resolve_scope_from_token(vault_ctx, token) is None:
            await JSONResponse({"error": "Unauthorized"}, status_code=401)(scope, receive, send)
            return
        auth_token = set_vault_context(vault_ctx, token)
        try:
            await manager.handle_request(scope, receive, send)
        finally:
            reset_vault_context(auth_token)

    class HttpEndpoint:
        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await streamable_http(scope, receive, send)

    routes = [
        Route("/mcp", endpoint=HttpEndpoint(), methods=["GET", "POST", "DELETE"]),
        Route("/api/v1/scopes/{scope_id}/codex-config", admin.codex_config, methods=["GET"]),
        Route("/api/v1/scopes/{scope_id}/token", admin.scope_token, methods=["GET"]),
        Route("/health", admin.health, methods=["GET"]),
        Route("/api/v1/status", admin.status, methods=["GET"]),
        Route("/api/v1/search", admin.search, methods=["POST"]),
        Route("/api/v1/reindex", admin.reindex, methods=["POST"]),
        Route("/api/v1/index-file", admin.index_file, methods=["POST"]),
        Route("/api/v1/llm/presets", admin.llm_presets, methods=["GET"]),
        Route("/api/v1/llm/status", admin.llm_status, methods=["GET"]),
        Route("/api/v1/llm/pull", admin.llm_pull, methods=["POST"]),
        Route("/api/v1/llm/pull-status", admin.llm_pull_status, methods=["GET"]),
        Route("/api/v1/llm/ask", admin.llm_ask, methods=["POST"]),
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
    return Starlette(routes=routes, lifespan=lifespan, middleware=[Middleware(AdminAuthorization)])
