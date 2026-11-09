"""Pytest configuration and global environment fixtures."""

import os

import pytest

# Ensure LiteLLM uses local cached model cost map and never hits the network during test runs
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "true"


@pytest.fixture(scope="session", autouse=True)
def hermetic_embedding_model():
    """Ensure tests run hermetically with dummy model unless explicitly overridden."""
    from app.analyzers.embeddings import EMBEDDING_DIM, set_embedding_model

    class DummyEmbeddingModel:
        def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
            return [[float(abs(hash(t)) % 1000) / 1000.0] * EMBEDDING_DIM for t in texts]

    dummy = DummyEmbeddingModel()
    set_embedding_model(dummy)
    yield dummy
    set_embedding_model(None)
