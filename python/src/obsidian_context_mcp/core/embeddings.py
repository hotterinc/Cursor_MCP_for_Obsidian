"""Embedding providers.

The default provider runs the embedding model through ONNX Runtime (int8),
which needs ~250 MB of RAM instead of the ~900 MB that PyTorch +
sentence-transformers took for the same model. Providers are cached per
process: every Indexer/Retriever shares one loaded model.
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx
from loguru import logger

from obsidian_context_mcp.core.app_paths import get_shared_models_cache_dir
from obsidian_context_mcp.core.locks import RuntimeLock
from obsidian_context_mcp.core.ml_runtime import configure_ml_runtime
from obsidian_context_mcp.shared.types import ProjectConfig

configure_ml_runtime()

ENV_EMBED_THREADS = "OBSIDIAN_CONTEXT_EMBED_THREADS"
EMBED_BATCH_SIZE = 16
# Cap padded tokens per batch: attention memory grows with batch * length^2, so
# 16 x 512 tokens needs ~400 MB of activations while 4 x 512 needs ~100 MB.
EMBED_BATCH_TOKENS = 2048


def _batches(lengths: list[int]) -> list[list[int]]:
    """Group indices (shortest first) into batches within the size and token caps."""
    order = sorted(range(len(lengths)), key=lambda i: lengths[i])
    batches: list[list[int]] = []
    current: list[int] = []
    for i in order:
        # Sorted ascending, so the newest item sets the padded width.
        if current and (
            len(current) >= EMBED_BATCH_SIZE or (len(current) + 1) * lengths[i] > EMBED_BATCH_TOKENS
        ):
            batches.append(current)
            current = []
        current.append(i)
    if current:
        batches.append(current)
    return batches


def _release_freed_memory() -> None:
    """Ask the macOS allocator to hand freed activation buffers back to the OS."""
    if sys.platform != "darwin":
        return
    try:
        import ctypes

        libc = ctypes.CDLL("/usr/lib/libSystem.B.dylib")
        libc.malloc_zone_pressure_relief(None, 0)
    except Exception:
        pass


@dataclass
class HealthResult:
    ok: bool
    message: str


class EmbeddingProvider(ABC):
    name: str
    dimensions: int

    @property
    def fingerprint(self) -> str:
        """Identifies the vector space; a change means stored vectors are stale."""
        return self.name

    @property
    def max_input_tokens(self) -> int | None:
        """Model input window, including prefix and special tokens (None = unknown)."""
        return None

    def count_tokens(self, text: str) -> int:
        """Tokens this text occupies in the model window when embedded as a passage."""
        return max(1, len(text) // 3)

    @abstractmethod
    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> HealthResult:
        raise NotImplementedError


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"
    dimensions = 64

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)

    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        prefix = "query: " if is_query else "passage: "
        return [self._embed_one(prefix + t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(self.dimensions):
            vec.append((digest[i % len(digest)] / 255.0) * 2 - 1)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def healthcheck(self) -> HealthResult:
        return HealthResult(ok=True, message="Fake embedding provider ready")


@dataclass(frozen=True)
class OnnxModelSpec:
    repo: str
    revision: str
    model_file: str
    # SentencePiece model; ~75 MB in memory vs ~330 MB for the tokenizers.json
    # version of the same 250k-piece XLM-R vocabulary.
    spm_file: str
    dimensions: int
    max_tokens: int = 512
    query_prefix: str = "query: "
    passage_prefix: str = "passage: "
    # fairseq/XLM-R id layout: model id = spm id + 1, with spm <unk>=0 mapped to 3.
    spm_offset: int = 1
    bos_id: int = 0
    pad_id: int = 1
    eos_id: int = 2
    unk_id: int = 3


ONNX_MODELS: dict[str, OnnxModelSpec] = {
    "intfloat/multilingual-e5-small": OnnxModelSpec(
        repo="intfloat/multilingual-e5-small",
        revision="614241f622f53c4eeff9890bdc4f31cfecc418b3",
        # Dynamic int8 quantisation published by the model authors; runs on any CPU.
        model_file="onnx/model_qint8_avx512_vnni.onnx",
        spm_file="onnx/sentencepiece.bpe.model",
        dimensions=384,
    ),
}


def _embed_threads() -> int:
    try:
        return max(1, int(os.environ.get(ENV_EMBED_THREADS, "1")))
    except ValueError:
        return 1


class OnnxEmbeddingProvider(EmbeddingProvider):
    """Mean-pooled transformer embeddings via ONNX Runtime (no PyTorch)."""

    name = "onnx"

    def __init__(self, model_name: str, cache_dir: str) -> None:
        spec = ONNX_MODELS.get(model_name)
        if spec is None:
            supported = ", ".join(sorted(ONNX_MODELS))
            raise ValueError(f"Embedding model {model_name!r} is not supported (supported: {supported})")
        self._spec = spec
        self._cache_dir = cache_dir
        self.dimensions = spec.dimensions
        self._tokenizer: Any = None
        self._session: Any = None
        self._input_names: set[str] = set()
        self._load_lock = threading.Lock()
        self._encode_lock = threading.Lock()

    @property
    def fingerprint(self) -> str:
        s = self._spec
        return f"onnx:{s.repo}@{s.revision[:12]}:{s.model_file}:{s.spm_file}"

    @property
    def max_input_tokens(self) -> int:
        return self._spec.max_tokens

    def _download(self, filename: str) -> str:
        from huggingface_hub import hf_hub_download

        kwargs: dict[str, Any] = {
            "repo_id": self._spec.repo,
            "filename": filename,
            "revision": self._spec.revision,
            "cache_dir": self._cache_dir,
        }
        try:
            return str(hf_hub_download(local_files_only=True, **kwargs))
        except Exception:
            logger.info("Downloading embedding model file {} from {}", filename, self._spec.repo)
            return str(hf_hub_download(**kwargs))

    def _load_tokenizer(self) -> Any:
        with self._load_lock:
            if self._tokenizer is None:
                import sentencepiece

                self._tokenizer = sentencepiece.SentencePieceProcessor(
                    model_file=self._download(self._spec.spm_file)
                )
            return self._tokenizer

    def _load_session(self) -> Any:
        self._load_tokenizer()
        with self._load_lock:
            if self._session is None:
                import onnxruntime as ort

                options = ort.SessionOptions()
                options.intra_op_num_threads = _embed_threads()
                options.inter_op_num_threads = 1
                options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                # The arena keeps the peak activation size reserved forever; skip it.
                options.enable_cpu_mem_arena = False
                options.log_severity_level = 3
                session = ort.InferenceSession(
                    self._download(self._spec.model_file),
                    sess_options=options,
                    providers=["CPUExecutionProvider"],
                )
                self._input_names = {i.name for i in session.get_inputs()}
                self._session = session
                logger.info("Loaded ONNX embedding model {}", self.fingerprint)
            return self._session

    def count_tokens(self, text: str) -> int:
        tokenizer = self._load_tokenizer()
        return len(tokenizer.encode(self._spec.passage_prefix + text)) + 2

    def _encode_ids(self, texts: list[str]) -> list[list[int]]:
        """Model input ids: <s> pieces </s>, truncated to the model window."""
        tokenizer = self._load_tokenizer()
        s = self._spec
        body_limit = s.max_tokens - 2
        out: list[list[int]] = []
        for pieces in tokenizer.encode(texts):
            body = [p + s.spm_offset if p else s.unk_id for p in pieces[:body_limit]]
            out.append([s.bos_id, *body, s.eos_id])
        return out

    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        if not texts:
            return []
        import numpy as np

        session = self._load_session()
        prefix = self._spec.query_prefix if is_query else self._spec.passage_prefix
        all_ids = self._encode_ids([prefix + t for t in texts])
        pad_id = self._spec.pad_id
        result: list[list[float]] = [[] for _ in texts]
        max_len = 0

        with self._encode_lock, RuntimeLock("embedding", timeout=600):
            # Similar lengths share a batch so short chunks are not padded to 512 tokens.
            for batch in _batches([len(ids) for ids in all_ids]):
                width = max(len(all_ids[i]) for i in batch)
                ids = np.full((len(batch), width), pad_id, dtype=np.int64)
                mask = np.zeros((len(batch), width), dtype=np.int64)
                for row, i in enumerate(batch):
                    seq = all_ids[i]
                    ids[row, : len(seq)] = seq
                    mask[row, : len(seq)] = 1
                feeds = {"input_ids": ids, "attention_mask": mask}
                if "token_type_ids" in self._input_names:
                    feeds["token_type_ids"] = np.zeros_like(ids)
                hidden = session.run(None, feeds)[0]
                weights = mask[..., None].astype(np.float32)
                pooled = (hidden * weights).sum(axis=1) / np.clip(weights.sum(axis=1), 1e-9, None)
                pooled /= np.clip(np.linalg.norm(pooled, axis=1, keepdims=True), 1e-12, None)
                for row, i in enumerate(batch):
                    result[i] = [float(v) for v in pooled[row]]
                max_len = max(max_len, width)
            if max_len > 128:
                _release_freed_memory()
        return result

    def healthcheck(self) -> HealthResult:
        try:
            self._load_session()
            return HealthResult(ok=True, message=f"Model {self._spec.repo} loaded (ONNX int8)")
        except Exception as exc:
            return HealthResult(ok=False, message=f"Model unavailable: {exc}")


class OllamaLocalEmbeddingProvider(EmbeddingProvider):
    name = "ollama"
    dimensions = 768

    def __init__(self, model: str, host: str = "http://127.0.0.1:11434") -> None:
        if not host.startswith("http://127.0.0.1") and not host.startswith("http://localhost"):
            raise ValueError("Ollama host must be localhost only")
        self._model = model
        self._host = host.rstrip("/")

    @property
    def fingerprint(self) -> str:
        return f"ollama:{self._model}"

    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        results = []
        with httpx.Client(timeout=120) as client:
            for text in texts:
                resp = client.post(
                    f"{self._host}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                resp.raise_for_status()
                data = resp.json()
                results.append(data["embedding"])
        return results

    def healthcheck(self) -> HealthResult:
        try:
            with httpx.Client(timeout=5) as client:
                resp = client.get(f"{self._host}/api/tags")
                resp.raise_for_status()
            return HealthResult(ok=True, message=f"Ollama available at {self._host}")
        except Exception as exc:
            return HealthResult(ok=False, message=str(exc))


# "sentence-transformers" is the provider name older configs were saved with; the
# same model now runs through ONNX Runtime.
_ONNX_PROVIDER_NAMES = {"onnx", "sentence-transformers"}

_providers: dict[tuple[str, ...], EmbeddingProvider] = {}
_providers_lock = threading.Lock()


def create_embedding_provider(config: ProjectConfig, project_id: str) -> EmbeddingProvider:
    """Return the process-wide provider for this config (models load once per process)."""
    provider = config.embedding_provider
    if provider == "fake":
        return FakeEmbeddingProvider()
    if provider == "ollama":
        key: tuple[str, ...] = ("ollama", config.embedding_model)
    elif provider in _ONNX_PROVIDER_NAMES:
        key = ("onnx", config.embedding_model, str(get_shared_models_cache_dir()))
    else:
        raise ValueError(f"Unknown embedding provider {provider!r}")

    with _providers_lock:
        cached = _providers.get(key)
        if cached is None:
            if key[0] == "ollama":
                cached = OllamaLocalEmbeddingProvider(config.embedding_model)
            else:
                cached = OnnxEmbeddingProvider(config.embedding_model, key[2])
            _providers[key] = cached
        return cached
