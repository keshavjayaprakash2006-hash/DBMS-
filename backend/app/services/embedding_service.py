"""
Embedding service supporting Google Gemini API embeddings and local Sentence-Transformers.
In production on Render, Gemini embeddings run with zero memory/PyTorch overhead.
Both providers generate 384-dimensional dense vectors to match the database schema.
"""
import logging
import time
from typing import List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_local_model = None
_local_model_name: Optional[str] = None


def _get_local_model():
    """Load and cache local sentence-transformers model (dev/offline fallback)."""
    global _local_model, _local_model_name
    if _local_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            model_name = settings.EMBEDDING_MODEL_NAME if settings.EMBEDDING_MODEL_NAME != "text-embedding-004" else "all-MiniLM-L6-v2"
            logger.info(f"Loading local embedding model: {model_name}")
            _local_model = SentenceTransformer(model_name)
            _local_model_name = model_name
        except Exception as e:
            logger.error(f"Failed to load local embedding model: {e}")
            raise RuntimeError(f"Local embedding model unavailable: {e}") from e
    return _local_model


def _generate_gemini_single_embedding(text_content: str, retries: int = 3) -> List[float]:
    """Generate 384-dimensional embedding via Google Gemini text-embedding-004."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for embedding service.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent?key={api_key}"
    payload = {
        "model": "models/text-embedding-004",
        "content": {"parts": [{"text": text_content[:8000]}]},  # Safe token window
        "outputDimensionality": settings.EMBEDDING_DIMENSION,
    }

    for attempt in range(retries):
        try:
            with httpx.Client(timeout=settings.GEMINI_TIMEOUT) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    values = data.get("embedding", {}).get("values", [])
                    if values:
                        return values
                    raise RuntimeError("Gemini returned empty embedding values.")
                elif resp.status_code in (429, 503):
                    wait_time = 1.5 * (attempt + 1)
                    logger.warning(f"Gemini embedding rate limited (HTTP {resp.status_code}). Backing off {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    err_msg = resp.text[:200]
                    raise RuntimeError(f"Gemini embedding API error: HTTP {resp.status_code} - {err_msg}")
        except httpx.RequestError as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"Gemini embedding network failure: {exc}") from exc
            time.sleep(1.0)

    raise RuntimeError("Gemini embedding failed after maximum retries.")


def _generate_gemini_batch_embeddings(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate batch embeddings via Gemini API batchEmbedContents."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for embedding service.")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:batchEmbedContents?key={api_key}"
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk_texts = texts[i : i + batch_size]
        requests_payload = [
            {
                "model": "models/text-embedding-004",
                "content": {"parts": [{"text": t[:8000]}]},
                "outputDimensionality": settings.EMBEDDING_DIMENSION,
            }
            for t in chunk_texts
        ]

        batch_success = False
        for attempt in range(3):
            try:
                with httpx.Client(timeout=settings.GEMINI_TIMEOUT) as client:
                    resp = client.post(url, json={"requests": requests_payload})
                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings_data = data.get("embeddings", [])
                        for item in embeddings_data:
                            all_embeddings.append(item.get("values", []))
                        batch_success = True
                        break
                    elif resp.status_code in (429, 503):
                        time.sleep(2.0 * (attempt + 1))
                    else:
                        raise RuntimeError(f"Gemini batch embedding error HTTP {resp.status_code}: {resp.text[:200]}")
            except httpx.RequestError:
                if attempt == 2:
                    raise
                time.sleep(1.0)

        if not batch_success:
            # Fallback to single calls for this chunk
            for t in chunk_texts:
                all_embeddings.append(_generate_gemini_single_embedding(t))

    return all_embeddings


def generate_embedding(text: str) -> List[float]:
    """Generate a single 384-dimensional embedding vector for given text."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            return _generate_gemini_single_embedding(text)
        except Exception as e:
            logger.warning(f"Gemini embedding failed ({e}), checking local fallback...")
            try:
                model = _get_local_model()
                emb = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
                return emb.tolist()
            except Exception:
                raise e

    # Local fallback
    model = _get_local_model()
    embedding = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
    return embedding.tolist()


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini" and settings.GEMINI_API_KEY:
        try:
            return _generate_gemini_batch_embeddings(texts, batch_size=batch_size)
        except Exception as e:
            logger.warning(f"Gemini batch embedding failed ({e}), checking local fallback...")
            try:
                model = _get_local_model()
                all_emb = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i : i + batch_size]
                    res = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                    all_emb.extend(res.tolist())
                return all_emb
            except Exception:
                raise e

    # Local fallback
    model = _get_local_model()
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
        all_embeddings.extend(embeddings.tolist())
    return all_embeddings


def check_embedding_service() -> dict:
    """Check if the configured embedding service is operational."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            return {
                "status": "unconfigured",
                "provider": "gemini",
                "model": "text-embedding-004",
                "dimension": settings.EMBEDDING_DIMENSION,
                "error": "GEMINI_API_KEY is not set. Add it to backend environment variables.",
            }
        try:
            test_emb = _generate_gemini_single_embedding("health check")
            return {
                "status": "ok",
                "provider": "gemini",
                "model": "text-embedding-004",
                "dimension": len(test_emb),
            }
        except Exception as e:
            return {
                "status": "error",
                "provider": "gemini",
                "model": "text-embedding-004",
                "dimension": settings.EMBEDDING_DIMENSION,
                "error": str(e),
            }

    # Local check
    try:
        model = _get_local_model()
        test_emb = generate_embedding("health check")
        return {
            "status": "ok",
            "provider": "local",
            "model": settings.EMBEDDING_MODEL_NAME,
            "dimension": len(test_emb),
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "local",
            "model": settings.EMBEDDING_MODEL_NAME,
            "error": str(e),
        }


def get_model_name() -> str:
    if settings.EMBEDDING_PROVIDER.lower().strip() == "gemini":
        return "text-embedding-004 (Gemini)"
    return settings.EMBEDDING_MODEL_NAME
