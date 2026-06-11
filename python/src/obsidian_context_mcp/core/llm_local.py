"""Built-in GGUF LLM download + inference (no Ollama app required)."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any, Callable

import httpx
from loguru import logger

from obsidian_context_mcp.core.vault_paths import get_vault_llm_models_dir

_LlamaType: Any = None
_llama_instance: Any = None
_llama_path: str | None = None
_llama_lock = threading.Lock()


def get_preset_by_id(preset_id: str) -> dict[str, str] | None:
    from obsidian_context_mcp.core.llm_service import LLM_PRESETS

    for p in LLM_PRESETS:
        if p["id"] == preset_id:
            return p
    return None


def local_model_path(data_dir: Path, preset_id: str) -> Path:
    preset = get_preset_by_id(preset_id)
    if preset is None:
        raise ValueError(f"Unknown preset: {preset_id}")
    safe_name = preset_id.replace(":", "_").replace("/", "_")
    return get_vault_llm_models_dir(data_dir) / safe_name / preset["hfFile"]


def local_model_available(data_dir: Path, preset_id: str) -> bool:
    try:
        path = local_model_path(data_dir, preset_id)
        return path.is_file() and path.stat().st_size > 1024 * 1024
    except ValueError:
        return False


def list_local_models(data_dir: Path) -> list[str]:
    out: list[str] = []
    from obsidian_context_mcp.core.llm_service import LLM_PRESETS

    for p in LLM_PRESETS:
        if local_model_available(data_dir, p["id"]):
            out.append(p["id"])
    return out


def download_gguf(
    repo: str,
    filename: str,
    dest: Path,
    *,
    on_progress: Callable[[int, int, str], None] | None = None,
) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    url = f"https://huggingface.co/{repo}/resolve/main/{filename}"
    completed = 0
    total = 0

    with httpx.Client(follow_redirects=True, timeout=None) as client:
        with client.stream("GET", url) as resp:
            resp.raise_for_status()
            cl = resp.headers.get("content-length")
            if cl:
                total = int(cl)
            with tmp.open("wb") as f:
                for chunk in resp.iter_bytes(1024 * 256):
                    if not chunk:
                        continue
                    f.write(chunk)
                    completed += len(chunk)
                    if on_progress:
                        on_progress(completed, total, "downloading")

    tmp.replace(dest)


def _load_llama(model_path: Path) -> Any:
    global _LlamaType, _llama_instance, _llama_path
    if _LlamaType is None:
        from llama_cpp import Llama

        _LlamaType = Llama

    path_str = str(model_path)
    with _llama_lock:
        if _llama_instance is not None and _llama_path == path_str:
            return _llama_instance
        if _llama_instance is not None:
            try:
                del _llama_instance
            except Exception:
                pass
            _llama_instance = None

        logger.info("Loading local LLM from {}", path_str)
        _llama_instance = _LlamaType(
            model_path=path_str,
            n_ctx=4096,
            n_gpu_layers=-1,
            verbose=False,
        )
        _llama_path = path_str
        return _llama_instance


def local_chat_completion(model_path: Path, prompt: str, *, timeout: float = 300) -> str:
    llama = _load_llama(model_path)
    with _llama_lock:
        result = llama.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1024,
        )
    choices = result.get("choices") or []
    if not choices:
        raise RuntimeError("Empty response from local LLM")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise RuntimeError("Empty content from local LLM")
    return str(content)


def local_pull_worker(
    data_dir: Path,
    preset_id: str,
    progress_cb: Callable[..., None],
) -> None:
    preset = get_preset_by_id(preset_id)
    if preset is None:
        progress_cb(error=f"Unknown preset {preset_id}")
        return
    dest = local_model_path(data_dir, preset_id)
    try:

        def on_prog(completed: int, total: int, status: str) -> None:
            progress_cb(completed=completed, total=total, status=status)

        progress_cb(status="downloading", completed=0, total=0)
        download_gguf(preset["hfRepo"], preset["hfFile"], dest, on_progress=on_prog)
        progress_cb(status="success")
    except Exception as exc:
        logger.exception("Local model download failed")
        if dest.exists():
            dest.unlink(missing_ok=True)
        progress_cb(error=str(exc))
