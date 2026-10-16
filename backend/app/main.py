"""
Semantic PYQ Analyzer & Study Heatmap - FastAPI Application
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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

    # Initialize database tables and pgvector
    try:
        with engine.connect() as conn:
            init_pgvector(conn)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
