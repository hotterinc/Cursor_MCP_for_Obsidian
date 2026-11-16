"""Unit tests for embedding providers."""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest

from obsidian_context_mcp.core import embeddings
from obsidian_context_mcp.core.embeddings import (
    OnnxEmbeddingProvider,
    create_embedding_provider,
)
from obsidian_context_mcp.shared.types import ProjectConfig


class _FakeTokenizer:
    """SentencePiece-like: one piece per whitespace word, spm ids start at 9."""

    def encode(self, text: str | list[str]) -> Any:
        if isinstance(text, list):
            return [self.encode(t) for t in text]
        return [9 + len(w) for w in text.split()]


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[dict[str, np.ndarray]] = []

    def run(self, _outputs: Any, feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.calls.append(feeds)
        ids = feeds["input_ids"].astype(np.float32)
        # hidden[b, t] = [id, 1, 0, ...]: mean pooling is easy to predict.
        hidden = np.zeros((*ids.shape, 4), dtype=np.float32)
        hidden[..., 0] = ids
        hidden[..., 1] = 1.0
        return [hidden]


@pytest.fixture
def provider(monkeypatch: pytest.MonkeyPatch) -> tuple[OnnxEmbeddingProvider, _FakeSession]:
    p = OnnxEmbeddingProvider("intfloat/multilingual-e5-small", "/tmp/models")
    session = _FakeSession()
    p._tokenizer = _FakeTokenizer()
    p._session = session
    p._input_names = {"input_ids", "attention_mask", "token_type_ids"}
    monkeypatch.setattr(embeddings, "RuntimeLock", lambda *a, **k: _NullLock())
    return p, session


class _NullLock:
    def __enter__(self) -> None:
        return None

    def __exit__(self, *args: object) -> None:
        return None


def test_onnx_embeddings_are_normalized_and_keep_input_order(provider: Any) -> None:
    p, session = provider
    texts = ["a much longer text with many words here", "short", "mid size text"]
    vectors = p.embed_texts(texts)

    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == 4
        assert abs(np.linalg.norm(v) - 1.0) < 1e-5
    # Same input → same vector regardless of batch position.
    again = p.embed_texts(["short"])
    assert np.allclose(again[0], vectors[1])
    assert "token_type_ids" in session.calls[0]


def test_onnx_padding_does_not_change_vectors(provider: Any) -> None:
    p, _ = provider
    alone = p.embed_texts(["short"])[0]
    padded = p.embed_texts(["short", "a much longer text " * 20])[0]
    assert np.allclose(alone, padded)


def test_onnx_truncates_to_model_window(provider: Any) -> None:
    p, session = provider
    p.embed_texts(["word " * 2000])
    ids = session.calls[-1]["input_ids"]
    assert ids.shape[1] == 512
    assert ids[0, 0] == 0 and ids[0, -1] == 2  # <s> ... </s> kept after truncation
    assert ids[0, 1] == 9 + len("passage:") + 1  # spm ids shifted by the fairseq offset


def test_onnx_query_and_passage_prefixes_differ(provider: Any) -> None:
    p, _ = provider
    assert p.count_tokens("hello world") == 2 + 1 + 2  # <s> passage: hello world </s>
    assert not np.allclose(p.embed_texts(["same"], is_query=True)[0], p.embed_texts(["same"])[0])


def test_unknown_onnx_model_is_rejected() -> None:
    with pytest.raises(ValueError, match="not supported"):
        OnnxEmbeddingProvider("some/other-model", "/tmp/models")


def test_provider_is_shared_per_process(tmp_path: Any) -> None:
    config = ProjectConfig(
        project_root=str(tmp_path),
        project_real_path=str(tmp_path),
        project_name="t",
        vault_path=str(tmp_path),
        vault_real_path=str(tmp_path),
    )
    first = create_embedding_provider(config, "a")
    second = create_embedding_provider(config, "b")
    assert first is second
    assert isinstance(first, OnnxEmbeddingProvider)

    legacy = config.model_copy(update={"embedding_provider": "sentence-transformers"})
    assert create_embedding_provider(legacy, "c") is first


def test_batches_respect_size_and_token_caps() -> None:
    lengths = [512] * 9 + [10] * 40
    batches = embeddings._batches(lengths)
    assert sorted(i for b in batches for i in b) == list(range(len(lengths)))
    for b in batches:
        assert len(b) <= embeddings.EMBED_BATCH_SIZE
        assert len(b) == 1 or len(b) * max(lengths[i] for i in b) <= embeddings.EMBED_BATCH_TOKENS
