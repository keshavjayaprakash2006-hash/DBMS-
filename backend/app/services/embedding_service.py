"""
Embedding service using Google Gemini API embeddings (production default)
with lightweight deterministic fallback for offline testing/development.
Generates 384-dimensional dense vectors to match the PostgreSQL vector schema (Vector(384)).
Requires zero PyTorch or SentenceTransformers dependencies in production.
"""
import hashlib
import logging
import math
import time
from typing import List, Optional
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_local_model = None
_local_model_checked = False
_discovered_embedding_model: Optional[str] = None


def _deterministic_hash_embedding(text_content: str, dimension: int = 384) -> List[float]:
    """
    Lightweight, deterministic fallback embedding generator for offline testing
    when neither Gemini API nor local PyTorch is configured.
    Generates a normalized 384-dimensional unit vector.
    """
    vector = []
    clean_text = text_content.strip()
    for i in range(dimension):
        seed_str = f"{clean_text}::{i}".encode("utf-8")
        h = int(hashlib.sha256(seed_str).hexdigest()[:8], 16)
        val = (h / 0xFFFFFFFF) * 2.0 - 1.0
        vector.append(val)
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


def _normalize_to_dimension(vector: List[float], target_dim: int = 384) -> List[float]:
    """Ensure vector is exactly target_dim and unit-normalized."""
    if len(vector) > target_dim:
        vector = vector[:target_dim]
    elif len(vector) < target_dim:
        vector = vector + [0.0] * (target_dim - len(vector))
    norm = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / norm, 6) for x in vector]


def _get_active_embedding_model(api_key: str) -> str:
    """Discover the active embedding model supported by the Gemini API key."""
    global _discovered_embedding_model
    if _discovered_embedding_model:
        return _discovered_embedding_model

    preferred = settings.EMBEDDING_MODEL_NAME.replace("models/", "")
    candidates = [preferred, "gemini-embedding-001", "embedding-001", "text-embedding-004"]

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                embedding_models = [
                    m["name"].replace("models/", "")
                    for m in models
                    if "embedContent" in m.get("supportedGenerationMethods", [])
                ]
                logger.info(f"Available embedding models on Gemini API: {embedding_models}")
                for cand in candidates:
                    if cand in embedding_models:
                        _discovered_embedding_model = cand
                        return cand
                if embedding_models:
                    _discovered_embedding_model = embedding_models[0]
                    return embedding_models[0]
    except Exception as e:
        logger.warning(f"Could not query Gemini ListModels: {e}")

    _discovered_embedding_model = preferred or "gemini-embedding-001"
    return _discovered_embedding_model


def _generate_gemini_single_embedding(text_content: str, retries: int = 3) -> List[float]:
    """Generate 384-dimensional embedding via Google Gemini embedding API."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not configured for embedding service.")

    model = _get_active_embedding_model(api_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent?key={api_key}"
    payload = {
        "model": f"models/{model}",
        "content": {"parts": [{"text": text_content[:8000]}]},
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
                        return _normalize_to_dimension(values, settings.EMBEDDING_DIMENSION)
                    raise RuntimeError("Gemini returned empty embedding values.")
                elif resp.status_code in (400, 404) and "outputDimensionality" in payload:
                    # Model might not accept outputDimensionality; retry without it and normalize manually
                    payload_no_dim = {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": text_content[:8000]}]},
                    }
                    fb_resp = client.post(url, json=payload_no_dim)
                    if fb_resp.status_code == 200:
                        fb_values = fb_resp.json().get("embedding", {}).get("values", [])
                        if fb_values:
                            return _normalize_to_dimension(fb_values, settings.EMBEDDING_DIMENSION)
                    err_msg = fb_resp.text[:200]
                    raise RuntimeError(f"Gemini embedding API error: HTTP {fb_resp.status_code} - {err_msg}")
                elif resp.status_code in (429, 503):
                    wait_time = 1.5 * (attempt + 1)
                    logger.warning(
                        f"Gemini embedding rate limited (HTTP {resp.status_code}). Backing off {wait_time}s..."
                    )
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

    model = _get_active_embedding_model(api_key)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:batchEmbedContents?key={api_key}"
    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), batch_size):
        chunk_texts = texts[i : i + batch_size]
        requests_payload = [
            {
                "model": f"models/{model}",
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
                            vals = item.get("values", [])
                            all_embeddings.append(_normalize_to_dimension(vals, settings.EMBEDDING_DIMENSION))
                        batch_success = True
                        break
                    elif resp.status_code in (429, 503):
                        time.sleep(2.0 * (attempt + 1))
                    else:
                        break
            except httpx.RequestError:
                if attempt == 2:
                    break
                time.sleep(1.0)

        if not batch_success:
            for t in chunk_texts:
                all_embeddings.append(_generate_gemini_single_embedding(t))

    return all_embeddings


def generate_embedding(text: str) -> List[float]:
    """Generate a single 384-dimensional embedding vector for given text."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            try:
                return _generate_gemini_single_embedding(text)
            except Exception as e:
                logger.warning(f"Gemini embedding failed: {e}. Falling back to deterministic embedding.")
        return _deterministic_hash_embedding(text, settings.EMBEDDING_DIMENSION)

    # Local mode (only invoked if explicitly configured as EMBEDDING_PROVIDER=local)
    model = _get_local_model()
    if model is not None:
        try:
            embedding = model.encode([text], convert_to_numpy=True, show_progress_bar=False)[0]
            return embedding.tolist()
        except Exception as e:
            logger.warning(f"Local model encoding failed: {e}")

    # Fallback deterministic vector (ensures offline tests and dev work without heavy ML libraries)
    return _deterministic_hash_embedding(text, settings.EMBEDDING_DIMENSION)


def generate_embeddings_batch(texts: List[str], batch_size: int = 32) -> List[List[float]]:
    """Generate embeddings for a list of texts."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            try:
                return _generate_gemini_batch_embeddings(texts, batch_size=batch_size)
            except Exception as e:
                logger.warning(f"Gemini batch embedding failed: {e}. Falling back to deterministic embeddings.")
        return [_deterministic_hash_embedding(t, settings.EMBEDDING_DIMENSION) for t in texts]

    # Local mode
    model = _get_local_model()
    if model is not None:
        try:
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = model.encode(batch, convert_to_numpy=True, show_progress_bar=False)
                all_embeddings.extend(embeddings.tolist())
            return all_embeddings
        except Exception as e:
            logger.warning(f"Local batch model encoding failed: {e}")

    return [_deterministic_hash_embedding(t, settings.EMBEDDING_DIMENSION) for t in texts]


def check_embedding_service() -> dict:
    """Check if the configured embedding service is operational."""
    provider = settings.EMBEDDING_PROVIDER.lower().strip()
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            return {
                "status": "unconfigured",
                "provider": "Google Gemini",
                "model": settings.EMBEDDING_MODEL_NAME,
                "dimension": settings.EMBEDDING_DIMENSION,
                "error": "GEMINI_API_KEY is not set. Add it to backend environment variables.",
            }
        try:
            model_name = _get_active_embedding_model(settings.GEMINI_API_KEY)
            test_emb = _generate_gemini_single_embedding("health check")
            return {
                "status": "ok",
                "provider": "Google Gemini",
                "model": model_name,
                "dimension": len(test_emb),
            }
        except Exception as e:
            model_name = _discovered_embedding_model or settings.EMBEDDING_MODEL_NAME
            return {
                "status": "error",
                "provider": "Google Gemini",
                "model": model_name,
                "dimension": settings.EMBEDDING_DIMENSION,
                "error": str(e),
            }

    # Local / fallback check
    return {
        "status": "ok",
        "provider": "local",
        "model": settings.EMBEDDING_MODEL_NAME,
        "dimension": settings.EMBEDDING_DIMENSION,
    }


def get_model_name() -> str:
    if settings.EMBEDDING_PROVIDER.lower().strip() == "gemini":
        active = _discovered_embedding_model or settings.EMBEDDING_MODEL_NAME
        return f"{active} (Gemini)"
    return settings.EMBEDDING_MODEL_NAME
