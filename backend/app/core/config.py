"""
MedAI Assistant - Application Configuration
Environment-based settings using Pydantic Settings.
"""
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── App ──────────────────────────────────────────────────────────────
    APP_NAME: str = "MedAI Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development | staging | production

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # ── Database ─────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./medai.db"
    DATABASE_ECHO: bool = False

    # ── JWT Authentication ───────────────────────────────────────────────
    JWT_SECRET_KEY: str = "medai-secret-change-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OpenAI ───────────────────────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: Optional[str] = None
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── ChromaDB ─────────────────────────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    CHROMA_COLLECTION_NAME: str = "medical_knowledge"

    # ── Web Search ───────────────────────────────────────────────────────
    GOOGLE_CSE_API_KEY: str = ""
    GOOGLE_CSE_ENGINE_ID: str = ""
    PUBMED_API_KEY: str = ""  # Optional: increases PubMed rate limit
    SEARCH_CACHE_TTL_MINUTES: int = 30
    SEARCH_MAX_RESULTS: int = 10
    WEB_SEARCH_ENABLED: bool = True  # Master toggle for web search

    # ── File Uploads ─────────────────────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20
    ALLOWED_FILE_TYPES: str = "pdf,jpg,jpeg,png"

    # ── Rate Limiting ────────────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = 30

    # ── Encryption ───────────────────────────────────────────────────────
    ENCRYPTION_KEY: str = ""  # Fernet key for patient data encryption

    # ── ML Models ────────────────────────────────────────────────────────
    ML_MODELS_DIR: str = "./ml_models"

    # ── Paths ────────────────────────────────────────────────────────────
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    @property
    def upload_path(self) -> Path:
        path = self.BASE_DIR / self.UPLOAD_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def ml_models_path(self) -> Path:
        path = self.BASE_DIR / self.ML_MODELS_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def chroma_path(self) -> Path:
        path = self.BASE_DIR / self.CHROMA_PERSIST_DIR
        path.mkdir(parents=True, exist_ok=True)
        return path

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()
