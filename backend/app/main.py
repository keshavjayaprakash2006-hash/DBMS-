"""
Semantic PYQ Analyzer & Study Heatmap - FastAPI Application
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from sqlalchemy import text
from app.core.config import settings
from app.core.logging import setup_logging
from app.db.database import engine, init_pgvector
from app.models.models import Base
from app.api import health, subjects, documents, pyqs, analysis, search, chat, dashboard

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME}")

    # Ensure upload directory exists
    os.makedirs(settings.UPLOAD_DIRECTORY, exist_ok=True)

    # Initialize database tables, pgvector, and HNSW indexes
    try:
        with engine.connect() as conn:
            init_pgvector(conn)
        Base.metadata.create_all(bind=engine)
        if engine.dialect.name == "postgresql":
            try:
                with engine.connect() as conn:
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_note_chunks_embedding_hnsw "
                        "ON note_chunks USING hnsw (embedding vector_cosine_ops)"
                    ))
                    conn.execute(text(
                        "CREATE INDEX IF NOT EXISTS idx_pyqs_embedding_hnsw "
                        "ON pyqs USING hnsw (embedding vector_cosine_ops)"
                    ))
                    conn.commit()
                    logger.info("pgvector HNSW indexes verified")
            except Exception as idx_err:
                logger.warning(f"Note on HNSW indexes: {idx_err}")
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        logger.warning("Application starting without database. Check DATABASE_URL in .env")

    yield
    logger.info("Application shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    description="Vector-database-powered study platform for PYQ analysis",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = settings.cors_origins_list
has_wildcard = "*" in cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if not has_wildcard else ["*"],
    allow_credentials=not has_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", tags=["Root"])
def root():
    return {
        "service": settings.APP_NAME,
        "status": "online",
        "docs": "/docs",
        "health": "/health",
    }

@app.get("/health", tags=["Health"])
def root_health():
    return {"status": "ok", "service": settings.APP_NAME}


# Include routers
app.include_router(health.router)
app.include_router(subjects.router)
app.include_router(documents.router)
app.include_router(pyqs.router)
app.include_router(analysis.router)
app.include_router(search.router)
app.include_router(chat.router)
app.include_router(dashboard.router)


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Check server logs."},
    )
