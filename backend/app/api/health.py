from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, text
from app.db.database import get_db, check_database_connection
from app.services.embedding_service import check_embedding_service
from app.services.chat_service import check_ollama
from app.schemas.schemas import SystemHealth, HealthStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
def health_check():
    return {"status": "ok", "service": "Semantic PYQ Analyzer"}


@router.get("/database")
def database_health():
    result = check_database_connection()
    return result


@router.get("/embedding")
def embedding_health():
    result = check_embedding_service()
    return result


@router.get("/ollama")
def ollama_health():
    result = check_ollama()
    return result


@router.get("/system", response_model=SystemHealth)
def system_health():
    db_result = check_database_connection()
    emb_result = check_embedding_service()
    ollama_result = check_ollama()

    db_ok = db_result.get("status") == "ok"
    pgv_ok = db_result.get("pgvector", False)
    emb_ok = emb_result.get("status") == "ok"
    ollama_ok = ollama_result.get("status") == "ok"

    overall = "ok" if (db_ok and pgv_ok and emb_ok) else "degraded"

    return SystemHealth(
        overall=overall,
        database=HealthStatus(
            status="ok" if db_ok else "error",
            details=db_result,
        ),
        pgvector=HealthStatus(
            status="ok" if pgv_ok else "unavailable",
            details={"available": pgv_ok},
        ),
        embedding=HealthStatus(
            status=emb_result.get("status"),
            details=emb_result,
        ),
        ollama=HealthStatus(
            status=ollama_result.get("status"),
            details=ollama_result,
        ),
    )
