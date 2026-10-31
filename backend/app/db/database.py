from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import QueuePool, NullPool
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

db_url = settings.normalized_database_url
is_sqlite = db_url.startswith("sqlite")

engine_kwargs = {
    "echo": settings.APP_ENV == "development",
}

if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["poolclass"] = QueuePool
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 10
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(db_url, **engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> dict:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            # Check pgvector
            try:
                pgvector_result = conn.execute(
                    text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
                ).fetchone()
                pgvector_available = pgvector_result is not None
            except Exception:
                pgvector_available = False
        return {
            "status": "ok",
            "pgvector": pgvector_available,
            "pgvector_enabled": pgvector_available,
            "dialect": engine.dialect.name,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "pgvector": False}


def init_pgvector(conn):
    """Enable pgvector extension if not already enabled."""
    try:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
        logger.info("pgvector extension enabled")
    except Exception as e:
        logger.warning(f"Could not enable pgvector: {e}")
