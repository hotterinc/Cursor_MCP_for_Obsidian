"""JSON-RPC 2.0 over stdio."""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from obsidian_context_mcp.gui_backend.schemas import RpcEvent, RpcRequest, RpcResponse


def configure_stdio_utf8() -> None:
    """Electron sends UTF-8 JSON; default Windows stdin may be cp1251."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


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
        sys.stdout.buffer.write(line.encode("utf-8"))
        sys.stdout.buffer.flush()

    def _write_response(self, response: RpcResponse) -> None:
        line = response.model_dump_json(exclude_none=True) + "\n"
        sys.stdout.buffer.write(line.encode("utf-8"))
        sys.stdout.buffer.flush()

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
        configure_stdio_utf8()
        with ThreadPoolExecutor(max_workers=4, thread_name_prefix="gui-rpc") as pool:
            for raw in sys.stdin.buffer:
                line = raw.decode("utf-8").strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    request = RpcRequest.model_validate(data)
                    pool.submit(self.handle_request, request)
                except Exception as exc:
                    self._write_response(
                        RpcResponse(error={"code": -32700, "message": f"Parse error: {exc}"})
                    )
