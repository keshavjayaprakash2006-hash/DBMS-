"""
Embedding service using Sentence-Transformers (local, offline).
The model is loaded once and cached for the lifetime of the process.
"""
import logging
from typing import List, Optional
import numpy as np

logger = logging.getLogger(__name__)

_model = None
_model_name: Optional[str] = None


def get_embedding_model():
    """Load and cache the sentence-transformers model."""
    global _model, _model_name
    from app.core.config import settings

    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            logger.info(f"Loading embedding model: {settings.EMBEDDING_MODEL_NAME}")
            _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            _model_name = settings.EMBEDDING_MODEL_NAME

            # Validate dimension
            test_embedding = _model.encode(["test"], convert_to_numpy=True)[0]
            actual_dim = len(test_embedding)
            if actual_dim != settings.EMBEDDING_DIMENSION:
                logger.warning(
                    f"Model '{settings.EMBEDDING_MODEL_NAME}' produces {actual_dim}-dim embeddings, "
                    f"but EMBEDDING_DIMENSION={settings.EMBEDDING_DIMENSION}. "
                    f"Update EMBEDDING_DIMENSION in .env to match."
                )
            logger.info(f"Embedding model loaded. Dimension: {actual_dim}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise RuntimeError(f"Embedding model unavailable: {e}") from e
    return _model


def generate_embedding(text: str) -> List[float]:
    """Generate a single embedding vector for given text."""
    model = get_embedding_model()
    embedding = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
    return embedding.tolist()


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for a list of texts in batches."""
    model = get_embedding_model()
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        embeddings = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())
    return all_embeddings


def check_embedding_service() -> dict:
    """Check if the embedding service is available."""
    try:
        model = get_embedding_model()
        test_emb = generate_embedding("health check")
        from app.core.config import settings
        return {
            "status": "ok",
            "model": settings.EMBEDDING_MODEL_NAME,
            "dimension": len(test_emb),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_model_name() -> Optional[str]:
    return _model_name
