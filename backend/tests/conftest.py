"""
Pytest configuration and fixtures for backend tests.
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Use SQLite for unit tests (no PostgreSQL required)
TEST_DATABASE_URL = "sqlite:///./test_pyq.db"

os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["EMBEDDING_MODEL_NAME"] = "all-MiniLM-L6-v2"
os.environ["EMBEDDING_DIMENSION"] = "384"
os.environ["UPLOAD_DIRECTORY"] = "./test_uploads"

from app.db.database import Base
from app.main import app


@pytest.fixture(scope="function")
def db_engine():
    """Create a test SQLite engine."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create a test database session."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="function")
def client(db_session):
    """Create a FastAPI test client with test database."""
    from app.db.database import get_db

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
