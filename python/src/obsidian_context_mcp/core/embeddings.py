"""Embedding providers."""

from __future__ import annotations

import hashlib
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from obsidian_context_mcp.core.app_paths import get_project_models_dir
from obsidian_context_mcp.shared.types import ProjectConfig


@dataclass
class HealthResult:
    ok: bool
    message: str


class EmbeddingProvider(ABC):
    name: str
    dimensions: int

    @abstractmethod
    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def healthcheck(self) -> HealthResult:
        raise NotImplementedError


class FakeEmbeddingProvider(EmbeddingProvider):
    name = "fake"
    dimensions = 64

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


class SentenceTransformersEmbeddingProvider(EmbeddingProvider):
    name = "sentence-transformers"
    dimensions = 384

    def __init__(self, model_name: str, cache_dir: str) -> None:
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name, cache_folder=self._cache_dir)
            dim = self._model.get_sentence_embedding_dimension()
            if dim:
                self.dimensions = dim
        return self._model

    def embed_texts(self, texts: list[str], *, is_query: bool = False) -> list[list[float]]:
        model = self._load_model()
        prefix = "query: " if is_query else "passage: "
        prefixed = [prefix + t for t in texts]
        vectors = model.encode(prefixed, show_progress_bar=False, normalize_embeddings=True)
        return [v.tolist() for v in vectors]

    def healthcheck(self) -> HealthResult:
        try:
            self._load_model()
            return HealthResult(ok=True, message=f"Model {self._model_name} loaded")
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


def create_embedding_provider(config: ProjectConfig, project_id: str) -> EmbeddingProvider:
    provider = config.embedding_provider
    if provider == "fake":
        return FakeEmbeddingProvider()
    if provider == "ollama":
        return OllamaLocalEmbeddingProvider(config.embedding_model)
    cache_dir = str(get_project_models_dir(project_id))
    return SentenceTransformersEmbeddingProvider(config.embedding_model, cache_dir)
