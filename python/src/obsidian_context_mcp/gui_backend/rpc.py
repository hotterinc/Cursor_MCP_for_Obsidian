"""JSON-RPC 2.0 over stdio."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from typing import Any

from obsidian_context_mcp.gui_backend.schemas import RpcEvent, RpcRequest, RpcResponse


class JsonRpcServer:
    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict], Any]] = {}
        self._event_sink: Callable[[RpcEvent], None] | None = None

    def register(self, method: str, handler: Callable[[dict], Any]) -> None:
        self._handlers[method] = handler

    def set_event_sink(self, sink: Callable[[RpcEvent], None]) -> None:
        self._event_sink = sink

    def emit_event(self, method: str, params: dict) -> None:
        event = RpcEvent(method=method, params=params)
        line = event.model_dump_json() + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def _write_response(self, response: RpcResponse) -> None:
        line = response.model_dump_json(exclude_none=True) + "\n"
        sys.stdout.write(line)
        sys.stdout.flush()

    def handle_request(self, request: RpcRequest) -> None:
        handler = self._handlers.get(request.method)
        if not handler:
            self._write_response(
                RpcResponse(
                    id=request.id,
                    error={"code": -32601, "message": f"Method not found: {request.method}"},
                )
            )
            return
        try:
            result = handler(request.params)
            self._write_response(RpcResponse(id=request.id, result=result if isinstance(result, dict) else {"data": result}))
        except Exception as exc:
            self._write_response(
                RpcResponse(
                    id=request.id,
                    error={"code": -32000, "message": str(exc)},
                )
            )

    def serve_stdio(self) -> None:
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                request = RpcRequest.model_validate(data)
                self.handle_request(request)
            except Exception as exc:
                self._write_response(
                    RpcResponse(error={"code": -32700, "message": f"Parse error: {exc}"})
                )
