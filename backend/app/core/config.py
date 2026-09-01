from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

INSECURE_JWT_DEFAULT = "change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    PROJECT_NAME: str = "Lead Agent API"
    API_V1_PREFIX: str = "/api/v1"
    # "development" (default) keeps insecure defaults usable for local work.
    # Set ENVIRONMENT=production to enforce secure config (see the validator).
    ENVIRONMENT: str = "development"

    # CORS — comma-separated origins allowed to call the API from a browser.
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # Infra
    DATABASE_URL: str = "postgresql+asyncpg://leadagent:leadagent@postgres:5432/leadagent"
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    JWT_SECRET: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day

    # Password reset (email-based forgot-password)
    RESET_TOKEN_EXPIRE_MINUTES: int = 30
    # Base URL of the frontend, used to build the reset link in the email.
    FRONTEND_BASE_URL: str = "http://localhost:3000"
    # Resend (https://resend.com) transactional email. When RESEND_API_KEY is
    # empty, the reset link is logged instead of emailed (dev-friendly).
    RESEND_API_KEY: str = ""
    EMAIL_FROM: str = "LeadLoop <onboarding@resend.dev>"

    # Chat LLM — pluggable provider that answers over retrieved chunks.
    #   LLM_PROVIDER=openai  -> openai SDK (default; needs OPENAI_API_KEY)
    #   LLM_PROVIDER=gemini  -> google-genai (shares the embedding key)
    LLM_PROVIDER: str = "openai"
    # Sentinel default — the factory treats this value as "unset" and lets the
    # selected provider pick its own default model (gpt-4o-mini / gemini-2.0-flash).
    # Set LLM_MODEL to any real model id to pin it.
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_API_KEY: str = ""
    # Retrieval knobs for the RAG chat.
    CHAT_TOP_K: int = 5  # chunks retrieved per question
    CHAT_MIN_SCORE: float = 0.3  # drop chunks below this cosine similarity
    # The public demo holds a higher bar than the internal chat: it is
    # unauthenticated, so a weak match should become a refusal rather than an
    # answer stretched from barely-relevant context.
    DEMO_MIN_SCORE: float = 0.45

    # Follow-up automation — a qualified/assigned lead with no activity for
    # STALL_HOURS gets an LLM-drafted follow-up email queued for human approval.
    STALL_HOURS: int = 48
    FOLLOWUP_CHECK_MINUTES: int = 60  # how often the beat task scans for stalls

    # OpenAI (used when LLM_PROVIDER=openai and/or EMBEDDING_PROVIDER=openai).
    # base_url is overridable so the same adapters work against any
    # OpenAI-compatible server (Azure OpenAI, local vLLM/Ollama, ...).
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = ""

    @property
    def llm_api_key(self) -> str:
        """The Gemini chat key, defaulting to the embedding key when unset."""
        return self.LLM_API_KEY or self.EMBEDDING_API_KEY

    # Embeddings — pluggable provider for the RAG pipeline.
    # Provider is selected at runtime; swapping it requires re-embedding stored
    # documents because the pgvector column is sized to one model's dimension.
    EMBEDDING_PROVIDER: str = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_API_KEY: str = ""  # unused for openai (uses OPENAI_API_KEY)
    EMBEDDING_DIM: int = 1536  # must match the active model + migration 0004

    # Document ingestion
    UPLOAD_DIR: str = "/data/uploads"
    # S3-compatible object storage (Cloudflare R2, MinIO, AWS S3). Uploads go to
    # the bucket when S3_BUCKET and S3_ENDPOINT_URL are both set; otherwise they
    # stay on local disk under UPLOAD_DIR. Required in any deployment where the
    # API and the worker don't share a filesystem.
    S3_ENDPOINT_URL: str = ""
    S3_BUCKET: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION: str = "auto"  # R2 uses "auto"
    S3_PREFIX: str = "uploads/"
    CHUNK_SIZE: int = 800  # approx tokens per chunk
    CHUNK_OVERLAP: int = 100

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize to the async driver in case a sync URL is supplied via env."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @model_validator(mode="after")
    def _enforce_production_security(self) -> "Settings":
        """In production, refuse to start with insecure defaults. In development
        these stay usable so local work is frictionless."""
        if self.ENVIRONMENT.lower() != "production":
            return self
        problems = []
        if self.JWT_SECRET in ("", INSECURE_JWT_DEFAULT):
            problems.append("JWT_SECRET must be set to a strong random value")
        if "leadagent:leadagent@" in self.DATABASE_URL:
            problems.append("DATABASE_URL still uses the default leadagent password")
        if problems:
            raise ValueError(
                "Insecure configuration for ENVIRONMENT=production: "
                + "; ".join(problems)
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
