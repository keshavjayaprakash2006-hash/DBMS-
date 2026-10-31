from fastapi import APIRouter, Depends
from app.db.database import check_database_connection
from app.services.embedding_service import check_embedding_service
from app.services.chat_service import check_ai_service, check_ollama
from app.services.storage_service import check_storage_service
from app.schemas.schemas import SystemHealth, HealthStatus
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/health", tags=["Health"])


@router.get("")
def health_check():
    return {"status": "ok", "service": "Semantic PYQ Analyzer"}


@router.get("/database")
def database_health():
    return check_database_connection()


@router.get("/embedding")
def embedding_health():
    return check_embedding_service()


@router.get("/ai")
def ai_health():
    return check_ai_service()


@router.get("/ollama")
def ollama_health():
    """Retained for frontend backward compatibility; checks AI assistant."""
    return check_ollama()


@router.get("/storage")
def storage_health():
    return check_storage_service()


@router.get("/system", response_model=SystemHealth)
def system_health():
    db_result = check_database_connection()
    emb_result = check_embedding_service()
    ai_result = check_ai_service()
    storage_result = check_storage_service()

    db_ok = db_result.get("status") == "ok"
    pgv_ok = db_result.get("pgvector", False)
    emb_ok = emb_result.get("status") == "ok"
    ai_ok = ai_result.get("status") == "ok"
    storage_ok = storage_result.get("status") == "ok"

    overall = "ok" if (db_ok and pgv_ok and emb_ok) else "degraded"

    ai_health_status = HealthStatus(
        status=ai_result.get("status", "unknown"),
        details=ai_result,
    )

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
            status=emb_result.get("status", "unknown"),
            details=emb_result,
        ),
        ollama=ai_health_status,
        ai=ai_health_status,
        storage=HealthStatus(
            status=storage_result.get("status", "unknown"),
            details=storage_result,
        ),
    )
