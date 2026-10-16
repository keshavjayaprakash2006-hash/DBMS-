"""
Ollama chat service for RAG-based study assistant.
Handles model availability, context construction, and error reporting.
"""
import logging
import httpx
from typing import List, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)


def check_ollama() -> dict:
    """Check if Ollama is running and the configured model is available."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if resp.status_code != 200:
                return {"status": "error", "error": f"Ollama returned HTTP {resp.status_code}"}
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            model_available = any(
                settings.OLLAMA_MODEL in m or m.startswith(settings.OLLAMA_MODEL)
                for m in models
            )
            return {
                "status": "ok" if model_available else "model_missing",
                "available_models": models,
                "configured_model": settings.OLLAMA_MODEL,
                "model_available": model_available,
            }
    except httpx.ConnectError:
        return {
            "status": "unavailable",
            "error": "Cannot connect to Ollama. Is it running? Install from https://ollama.ai and run: ollama serve",
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def build_rag_prompt(question: str, chunks: List[dict], pyqs: List[dict]) -> str:
    """Build the RAG prompt with retrieved study context."""
    context_parts = []
    for i, chunk in enumerate(chunks[:5]):  # Limit to top 5 chunks
        context_parts.append(
            f"[Study Material {i+1} - {chunk.get('document_filename', 'Notes')}]\n{chunk['content']}"
        )

    if pyqs:
        context_parts.append("\n[Related Previous Year Questions]")
        for pyq in pyqs[:3]:
            context_parts.append(
                f"- {pyq['exam_year']} ({pyq['marks']} marks): {pyq['question']}"
            )

    context = "\n\n".join(context_parts)

    return f"""You are an academic study assistant. Answer the student's question using ONLY the provided study material below.

If the study material does not contain enough information to answer the question, say so clearly - do NOT invent information.

STUDY MATERIAL:
{context}

STUDENT QUESTION: {question}

Provide a clear, accurate answer based on the study material above. If relevant, mention which topics or sections the information comes from."""


def generate_chat_response(
    question: str,
    chunks: List[dict],
    pyqs: List[dict],
) -> Tuple[str, Optional[str]]:
    """
    Generate a response using Ollama.
    Returns (answer_text, error_message).
    error_message is None on success.
    """
    ollama_status = check_ollama()

    if ollama_status["status"] == "unavailable":
        return "", (
            "Ollama is not running. To use the AI chat feature:\n"
            "1. Install Ollama from https://ollama.ai\n"
            "2. Run: ollama serve\n"
            f"3. Pull the model: ollama pull {settings.OLLAMA_MODEL}\n\n"
            "The rest of the application (search, heatmap, uploads) works without Ollama."
        )

    if ollama_status["status"] == "model_missing":
        available = ", ".join(ollama_status.get("available_models", []))
        return "", (
            f"Ollama is running but model '{settings.OLLAMA_MODEL}' is not available.\n"
            f"Run: ollama pull {settings.OLLAMA_MODEL}\n"
            f"Available models: {available or 'none'}"
        )

    prompt = build_rag_prompt(question, chunks, pyqs)

    try:
        with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
            resp = client.post(
                f"{settings.OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            if resp.status_code != 200:
                return "", f"Ollama API error: HTTP {resp.status_code} - {resp.text[:200]}"
            data = resp.json()
            answer = data.get("response", "").strip()
            if not answer:
                return "", "Ollama returned an empty response."
            return answer, None
    except httpx.TimeoutException:
        return "", (
            f"Ollama request timed out after {settings.OLLAMA_TIMEOUT}s. "
            "The model may be loading or the question may be too complex. Try again."
        )
    except Exception as e:
        return "", f"Error communicating with Ollama: {e}"
