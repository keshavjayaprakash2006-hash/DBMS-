from pydantic_settings import BaseSettings
from typing import List, Optional
import os


class Settings(BaseSettings):
    APP_NAME: str = "Semantic PYQ Analyzer"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    PORT: Optional[int] = None

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/pyq_analyzer"

    # AI Assistant (Google Gemini API)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_TIMEOUT: int = 45

    # Embedding Service
    # "gemini" uses Google Gemini text-embedding-004 (lightweight, zero memory overhead on Render)
    # "local" uses Sentence-Transformers all-MiniLM-L6-v2 (offline PyTorch)
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL_NAME: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 384

    # Cloud Object Storage (Supabase Storage)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_STORAGE_BUCKET: str = "documents"

    # Legacy Ollama settings (retained for backward compatibility)
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_TIMEOUT: int = 120

    UPLOAD_DIRECTORY: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    TOP_K_MATCHES: int = 3
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,*"

    LOG_LEVEL: str = "INFO"

    @property
    def effective_port(self) -> int:
        if self.PORT is not None:
            return self.PORT
        port_env = os.environ.get("PORT")
        if port_env:
            try:
                return int(port_env)
            except ValueError:
                pass
        return self.APP_PORT

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def normalized_database_url(self) -> str:
        """Ensure DATABASE_URL uses the psycopg driver and proper dialect."""
        url = self.DATABASE_URL.strip()
        # Handle SQLite for testing
        if url.startswith("sqlite"):
            return url
        # Handle postgresql:// or postgres://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
