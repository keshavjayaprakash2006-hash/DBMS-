"""
AI Chat & Study Assistant Service using Google Gemini API with RAG grounding.
Replaces the local Ollama dependency completely with cloud-hosted Gemini text generation.
"""
import logging
import time
from typing import List, Optional, Tuple, Dict, Any
import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_discovered_chat_model: Optional[str] = None


def _get_active_chat_model(api_key: str) -> str:
    """Discover the active text generation model supported by the Gemini API key."""
    global _discovered_chat_model
    if _discovered_chat_model:
        return _discovered_chat_model

    preferred = settings.GEMINI_MODEL.replace("models/", "")
    candidates = ["gemini-3.8-flash", preferred, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-pro"]

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                models = data.get("models", [])
                chat_models = [
                    m["name"].replace("models/", "")
                    for m in models
                    if "generateContent" in m.get("supportedGenerationMethods", [])
                ]
                logger.info(f"Available chat models on Gemini API: {chat_models}")
                for cand in candidates:
                    if cand in chat_models:
                        _discovered_chat_model = cand
                        return cand
                if chat_models:
                    _discovered_chat_model = chat_models[0]
                    return chat_models[0]
    except Exception as e:
        logger.warning(f"Could not list Gemini chat models: {e}")

    _discovered_chat_model = "gemini-3.8-flash"
    return _discovered_chat_model


def check_ai_service() -> Dict[str, Any]:
    """Check Google Gemini API configuration and connectivity."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return {
            "status": "unconfigured",
            "provider": "Google Gemini",
            "model": settings.GEMINI_MODEL,
            "error": "GEMINI_API_KEY environment variable is not set. Add it in Render Dashboard settings.",
        }

    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    model = _get_active_chat_model(api_key)

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}?key={api_key}"
        with httpx.Client(timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                display_name = data.get("displayName", model)
                return {
                    "status": "ok",
                    "provider": "Google Gemini",
                    "model": model,
                    "display_name": display_name,
                    "masked_key": masked_key,
                }
            elif resp.status_code == 400:
                return {
                    "status": "error",
                    "provider": "Google Gemini",
                    "model": model,
                    "error": "Invalid Gemini API key. Please check your key in settings.",
                }
            elif resp.status_code == 404:
                # Try fallback model check
                return {
                    "status": "warning",
                    "provider": "Google Gemini",
                    "model": model,
                    "error": f"Model '{model}' not found. Consider using gemini-2.5-flash or gemini-1.5-flash.",
                }
            elif resp.status_code == 429:
                return {
                    "status": "warning",
                    "provider": "Google Gemini",
                    "model": model,
                    "error": "Gemini API rate limit reached (HTTP 429).",
                }
            else:
                return {
                    "status": "error",
                    "provider": "Google Gemini",
                    "model": model,
                    "error": f"HTTP {resp.status_code}: {resp.text[:150]}",
                }
    except httpx.TimeoutException:
        return {
            "status": "timeout",
            "provider": "Google Gemini",
            "model": model,
            "error": "Connection to Google Gemini timed out.",
        }
    except Exception as e:
        return {
            "status": "error",
            "provider": "Google Gemini",
            "model": model,
            "error": f"Connection error: {str(e)}",
        }


def check_ollama() -> Dict[str, Any]:
    """Backward compatibility alias for health endpoints and settings."""
    status_info = check_ai_service()
    return {
        "status": status_info.get("status"),
        "provider": status_info.get("provider", "Google Gemini"),
        "configured_model": status_info.get("model", settings.GEMINI_MODEL),
        "active_model": status_info.get("model", settings.GEMINI_MODEL),
        "model_available": status_info.get("status") == "ok",
        "available_models": [settings.GEMINI_MODEL],
        "error": status_info.get("error"),
    }


def build_rag_prompt(question: str, chunks: List[dict], pyqs: List[dict]) -> str:
    """Build the RAG prompt with retrieved study context and strict academic grounding."""
    context_parts = []
    if chunks:
        for i, chunk in enumerate(chunks[:5]):
            doc_name = chunk.get("document_filename") or "Course Notes"
            context_parts.append(
                f"[Study Material {i+1} - {doc_name}]\n{chunk.get('content', '')}"
            )
    else:
        context_parts.append("[No specific study material chunks matched this query]")

    if pyqs:
        context_parts.append("\n[Related Previous Year Questions (PYQs)]")
        for pyq in pyqs[:3]:
            context_parts.append(
                f"- {pyq.get('exam_year')} ({pyq.get('marks')} marks): {pyq.get('question')}"
            )

    context = "\n\n".join(context_parts)

    return f"""You are an expert academic study assistant for university computer science and engineering students.
Your primary objective is to answer the student's question accurately, grounded STRICTLY in the provided study material.

GROUNDING RULES:
1. Use the provided STUDY MATERIAL below to explain concepts, give definitions, and answer the question.
2. If the study material explicitly covers the topic, provide a clear, well-structured, educational explanation citing the relevant sections.
3. If the provided study material does NOT contain sufficient information to answer the question, state honestly and clearly:
   "The uploaded course notes and materials do not contain sufficient information to answer this question thoroughly."
   Then, provide a brief, general academic explanation while explicitly clarifying that it was not found in the uploaded notes.
4. If related Previous Year Questions are listed, briefly highlight how this topic has appeared in past exams and how many marks it typically carries.

STUDY MATERIAL:
{context}

STUDENT QUESTION:
{question}

Provide a comprehensive, structured response:"""


def _call_gemini_api(prompt: str, model: str, api_key: str, retries: int = 3) -> Tuple[str, Optional[str]]:
    """Execute API call to Gemini with exponential backoff on transient errors."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "topP": 0.95,
            "maxOutputTokens": 2048,
        },
    }

    last_error = None
    for attempt in range(retries):
        try:
            with httpx.Client(timeout=settings.GEMINI_TIMEOUT) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        text_parts = [p.get("text", "") for p in parts if "text" in p]
                        answer = "".join(text_parts).strip()
                        if answer:
                            return answer, None
                    return "", "Gemini API returned an empty response. Try rephrasing your question."
                elif resp.status_code in (429, 503):
                    wait_time = 2.0 * (attempt + 1)
                    logger.warning(f"Gemini API rate limited (429). Attempt {attempt+1}/{retries}, waiting {wait_time}s...")
                    time.sleep(wait_time)
                    last_error = "Gemini API rate limit or quota exceeded. Please wait a moment and try again."
                elif resp.status_code == 400:
                    return "", f"Invalid request or API key (HTTP 400): {resp.text[:200]}"
                elif resp.status_code == 403:
                    return "", "Gemini API key is invalid or lacks necessary permissions."
                else:
                    last_error = f"Gemini API error (HTTP {resp.status_code}): {resp.text[:200]}"
        except httpx.TimeoutException:
            last_error = f"Gemini API request timed out after {settings.GEMINI_TIMEOUT} seconds. Please try again."
        except httpx.RequestError as e:
            last_error = f"Network connection error to Gemini API: {str(e)}"
            time.sleep(1.0)

    return "", last_error or "Failed to generate answer from Gemini API after retries."


def generate_chat_response(
    question: str,
    chunks: List[dict],
    pyqs: List[dict],
) -> Tuple[str, Optional[str]]:
    """
    Generate a study assistant response grounded in retrieved note chunks.
    Returns (answer_text, error_message).
    """
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        return "", (
            "Google Gemini API is not configured on the server.\n\n"
            "To enable the AI Study Assistant:\n"
            "1. Obtain a free API key at https://aistudio.google.com/app/apikey\n"
            "2. Set the `GEMINI_API_KEY` environment variable in your Render Web Service dashboard.\n\n"
            "All other features (Semantic Search, Heatmap, PYQ Library, Uploads) continue to work!"
        )

    prompt = build_rag_prompt(question, chunks, pyqs)
    model = _get_active_chat_model(api_key)

    answer, error = _call_gemini_api(prompt, model, api_key)
    if answer:
        return answer, None

    # If configured model failed with 404 or unsupported, attempt fallback to gemini-1.5-flash
    if error and ("not found" in error.lower() or "404" in error or "503" in error):
        logger.info("Attempting fallback to gemini-1.5-flash...")
        fb_answer, fb_error = _call_gemini_api(prompt, "gemini-2.5-flash", api_key)
        if fb_answer:
            return fb_answer, None
        return "", fb_error

    return "", error
