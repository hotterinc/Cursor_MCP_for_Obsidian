"""Local LLM for vault Q&A — built-in GGUF (preset) or Ollama (custom)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"

LLM_PRESETS: list[dict[str, str]] = [
    {
        "id": "qwen2.5:0.5b",
        "name": "Qwen 2.5 0.5B",
        "tier": "small",
        "sizeHint": "~400 MB",
        "description": "Самая лёгкая, быстрый старт",
        "hfRepo": "Qwen/Qwen2.5-0.5B-Instruct-GGUF",
        "hfFile": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "backend": "local",
    },
    {
        "id": "phi3:mini",
        "name": "Phi-3 Mini",
        "tier": "small",
        "sizeHint": "~2.3 GB",
        "description": "Компактная модель Microsoft",
        "hfRepo": "microsoft/Phi-3-mini-4k-instruct-gguf",
        "hfFile": "Phi-3-mini-4k-instruct-q4.gguf",
        "backend": "local",
    },
    {
        "id": "gemma2:2b",
        "name": "Gemma 2 2B",
        "tier": "small",
        "sizeHint": "~1.6 GB",
        "description": "Google, баланс скорости и качества",
        "hfRepo": "bartowski/gemma-2-2b-it-GGUF",
        "hfFile": "gemma-2-2b-it-Q4_K_M.gguf",
        "backend": "local",
    },
    {
        "id": "qwen2.5:3b",
        "name": "Qwen 2.5 3B",
        "tier": "medium",
        "sizeHint": "~2 GB",
        "description": "Лучше по-русски, чем 0.5B",
        "hfRepo": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "hfFile": "qwen2.5-3b-instruct-q4_k_m.gguf",
        "backend": "local",
    },
    {
        "id": "llama3.2:3b",
        "name": "Llama 3.2 3B",
        "tier": "medium",
        "sizeHint": "~2 GB",
        "description": "Универсальная средняя модель",
        "hfRepo": "QuantFactory/Meta-Llama-3.2-3B-Instruct-GGUF",
        "hfFile": "Meta-Llama-3.2-3B-Instruct.Q4_K_M.gguf",
        "backend": "local",
    },
    {
        "id": "mistral:7b-instruct-q4_0",
        "name": "Mistral 7B (Q4)",
        "tier": "medium",
        "sizeHint": "~4 GB",
        "description": "Качественнее, но тяжелее",
        "hfRepo": "QuantFactory/Mistral-7B-Instruct-v0.3-GGUF",
        "hfFile": "Mistral-7B-Instruct-v0.3.Q4_0.gguf",
        "backend": "local",
    },
]


def normalize_ollama_host(host: str) -> str:
    h = host.strip().rstrip("/")
    if not h.startswith("http://127.0.0.1") and not h.startswith("http://localhost"):
        raise ValueError("Ollama host must be localhost only")
    return h


@dataclass
class PullProgress:
    active: bool = False
    model: str = ""
    status: str = ""
    completed: int = 0
    total: int = 0
    error: str | None = None
    backend: str = "local"

    def to_dict(self) -> dict[str, Any]:
        pct = 0
        if self.total > 0:
            pct = min(100, int(self.completed * 100 / self.total))
        return {
            "active": self.active,
            "model": self.model,
            "status": self.status,
            "completed": self.completed,
            "total": self.total,
            "percent": pct,
            "error": self.error,
            "backend": self.backend,
        }


class LlmPullManager:
    _instance: LlmPullManager | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._progress = PullProgress()
        self._progress_lock = threading.Lock()

    @classmethod
    def get(cls) -> LlmPullManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = LlmPullManager()
        return cls._instance

    def get_progress(self) -> dict[str, Any]:
        with self._progress_lock:
            return self._progress.to_dict()

    def start_local_pull(self, data_dir: Path, preset_id: str) -> dict[str, Any]:
        with self._progress_lock:
            if self._progress.active:
                return self._progress.to_dict()
            self._progress = PullProgress(
                active=True, model=preset_id, status="starting", backend="local"
            )

        thread = threading.Thread(
            target=self._local_pull_worker,
            args=(data_dir, preset_id),
            daemon=True,
        )
        thread.start()
        return self.get_progress()

    def _local_pull_worker(self, data_dir: Path, preset_id: str) -> None:
        from obsidian_context_mcp.core.llm_local import local_pull_worker

        def progress_cb(
            *,
            completed: int = 0,
            total: int = 0,
            status: str = "",
            error: str | None = None,
        ) -> None:
            with self._progress_lock:
                if status:
                    self._progress.status = status
                if total:
                    self._progress.total = total
                if completed:
                    self._progress.completed = completed
                if error:
                    self._progress.error = error

        try:
            local_pull_worker(data_dir, preset_id, progress_cb)
        except Exception as exc:
            logger.exception("Local pull failed")
            with self._progress_lock:
                self._progress.error = str(exc)
        finally:
            with self._progress_lock:
                self._progress.active = False
                if not self._progress.error:
                    self._progress.status = "success"

    def start_ollama_pull(self, host: str, model: str) -> dict[str, Any]:
        with self._progress_lock:
            if self._progress.active:
                return self._progress.to_dict()
            self._progress = PullProgress(
                active=True, model=model, status="starting", backend="ollama"
            )

        thread = threading.Thread(
            target=self._ollama_pull_worker, args=(host, model), daemon=True
        )
        thread.start()
        return self.get_progress()

    def _ollama_pull_worker(self, host: str, model: str) -> None:
        try:
            base = normalize_ollama_host(host)
            with httpx.Client(timeout=None) as client:
                with client.stream(
                    "POST",
                    f"{base}/api/pull",
                    json={"name": model, "stream": True},
                ) as resp:
                    resp.raise_for_status()
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        data = json.loads(line)
                        with self._progress_lock:
                            self._progress.status = str(data.get("status", ""))
                            total = data.get("total")
                            completed = data.get("completed")
                            if isinstance(total, int):
                                self._progress.total = total
                            if isinstance(completed, int):
                                self._progress.completed = completed
                            if data.get("error"):
                                self._progress.error = str(data["error"])
        except Exception as exc:
            logger.exception("Ollama pull failed")
            with self._progress_lock:
                self._progress.error = str(exc)
        finally:
            with self._progress_lock:
                self._progress.active = False
                if not self._progress.error:
                    self._progress.status = "success"


def list_installed_ollama_models(host: str) -> list[str]:
    base = normalize_ollama_host(host)
    with httpx.Client(timeout=15) as client:
        resp = client.get(f"{base}/api/tags")
        resp.raise_for_status()
        data = resp.json()
    names: list[str] = []
    for item in data.get("models", []):
        name = item.get("name") or item.get("model")
        if name:
            names.append(str(name))
    return names


def ollama_health(host: str) -> dict[str, Any]:
    try:
        base = normalize_ollama_host(host)
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{base}/api/tags")
            resp.raise_for_status()
        return {"ok": True, "host": base, "backend": "ollama"}
    except Exception as exc:
        return {"ok": False, "host": host, "backend": "ollama", "error": str(exc)}


def ollama_model_available(host: str, model: str) -> bool:
    try:
        installed = list_installed_ollama_models(host)
    except Exception:
        return False
    if model in installed:
        return True
    prefix = model.split(":")[0] if ":" in model else model
    return any(m == model or m.startswith(f"{model}:") or m.startswith(prefix) for m in installed)


def build_rag_prompt(query: str, chunks: list[dict[str, Any]]) -> str:
    if not chunks:
        return (
            "В vault не найдено релевантных заметок для этого вопроса. "
            f"Вопрос пользователя: {query}"
        )
    parts: list[str] = []
    for i, c in enumerate(chunks, 1):
        path = c.get("relative_path", "")
        title = c.get("title", "")
        text = c.get("text", "")
        parts.append(f"[{i}] {title} ({path})\n{text}")
    context = "\n\n".join(parts)
    return (
        "Ты помощник по личному Obsidian vault. Ответь на вопрос пользователя, "
        "используя ТОЛЬКО приведённый контекст из заметок. "
        "Если ответа нет в контексте — честно скажи. "
        "Отвечай на том же языке, что и вопрос. "
        "В конце перечисли номера источников [1], [2]… которые использовал.\n\n"
        f"Контекст:\n{context}\n\n"
        f"Вопрос: {query}"
    )


def ollama_chat_completion(host: str, model: str, prompt: str, *, timeout: float = 300) -> str:
    base = normalize_ollama_host(host)
    with httpx.Client(timeout=timeout) as client:
        resp = client.post(
            f"{base}/api/chat",
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    message = data.get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Empty response from Ollama")
    return str(content)


@dataclass
class AskResult:
    answer: str
    sources: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"answer": self.answer, "sources": self.sources}


def local_model_exists(data_dir: Path, preset_id: str) -> bool:
    from obsidian_context_mcp.core.llm_local import local_model_available

    return local_model_available(data_dir, preset_id)


def ask_with_rag(
    ctx: Any,
    query: str,
    model: str,
    *,
    backend: str = "local",
    host: str = DEFAULT_OLLAMA_HOST,
    data_dir: Path | None = None,
    top_k: int = 8,
) -> AskResult:
    from obsidian_context_mcp.core.retrieval import Retriever
    from obsidian_context_mcp.shared.types import SearchMode

    retriever = Retriever(ctx)
    results = retriever.search(query, top_k=top_k, mode=SearchMode.HYBRID)
    chunks = [r.model_dump() for r in results]
    sources = [
        {
            "relative_path": c["relative_path"],
            "title": c["title"],
            "score": c["score"],
            "excerpt": (c.get("text") or "")[:200],
        }
        for c in chunks
    ]
    prompt = build_rag_prompt(query, chunks)

    if backend == "local":
        if data_dir is None:
            raise ValueError("data_dir required for local LLM")
        from obsidian_context_mcp.core.llm_local import local_chat_completion, local_model_path

        path = local_model_path(data_dir, model)
        if not path.is_file():
            raise FileNotFoundError(f"Model not downloaded: {model}")
        answer = local_chat_completion(path, prompt)
    else:
        answer = ollama_chat_completion(host, model, prompt)

    return AskResult(answer=answer, sources=sources)
