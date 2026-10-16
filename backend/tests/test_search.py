"""
Tests for semantic search endpoints and embedding service.
"""
import pytest
from app.services import embedding_service


def test_embedding_service_dimensions():
    """Embedding service generates vectors of correct dimension (384)."""
    emb = embedding_service.generate_embedding("What is an operating system kernel?")
    assert isinstance(emb, list)
    assert len(emb) == 384
    assert all(isinstance(x, float) for x in emb)


def test_embedding_service_deterministic():
    """Same text produces identical embeddings."""
    text = "Relational database management systems and ACID properties."
    emb1 = embedding_service.generate_embedding(text)
    emb2 = embedding_service.generate_embedding(text)
    assert emb1 == emb2


def test_semantic_search_empty_query(client):
    """Empty query should return 422 Unprocessable Entity."""
    resp = client.post("/api/search/semantic", json={"query": "   ", "top_k": 5})
    assert resp.status_code == 422
