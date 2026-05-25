"""Unit tests for embedding providers."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np

from obsidian_context_mcp.core.embeddings import SentenceTransformersEmbeddingProvider


def test_sentence_transformers_encode_uses_numpy_path() -> None:
    provider = SentenceTransformersEmbeddingProvider("test-model", "/tmp/models")
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = np.zeros((2, 384), dtype=np.float32)

    with patch.object(provider, "_load_model", return_value=mock_model):
        vectors = provider.embed_texts(["hello", "world"], is_query=False)

    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    mock_model.encode.assert_called_once()
    kwargs = mock_model.encode.call_args.kwargs
    assert kwargs["convert_to_numpy"] is True
    assert kwargs["convert_to_tensor"] is False
    assert kwargs["device"] == "cpu"
