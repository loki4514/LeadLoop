from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    PROJECT_NAME: str = "Lead Agent API"
    API_V1_PREFIX: str = "/api/v1"

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

    # Chat LLM — Gemini generative model used to answer over retrieved chunks.
    # Shares the Gemini/google-genai SDK with embeddings. If LLM_API_KEY is left
    # blank it falls back to EMBEDDING_API_KEY (same Google API key in practice).
    LLM_MODEL: str = "gemini-2.0-flash"
    LLM_API_KEY: str = ""
    # Retrieval knobs for the RAG chat.
    CHAT_TOP_K: int = 5  # chunks retrieved per question
    CHAT_MIN_SCORE: float = 0.3  # drop chunks below this cosine similarity

    @property
    def llm_api_key(self) -> str:
        """The chat model's key, defaulting to the embedding key when unset."""
        return self.LLM_API_KEY or self.EMBEDDING_API_KEY

    # Embeddings — pluggable provider for the RAG pipeline.
    # Provider is selected at runtime; swapping it requires re-embedding stored
    # documents because the pgvector column is sized to one model's dimension.
    EMBEDDING_PROVIDER: str = "gemini"
    EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_API_KEY: str = ""
    EMBEDDING_DIM: int = 768  # must match the active model; see migration

    # Document ingestion
    UPLOAD_DIR: str = "/data/uploads"
    CHUNK_SIZE: int = 800  # approx tokens per chunk
    CHUNK_OVERLAP: int = 100

    @property
    def sqlalchemy_url(self) -> str:
        """Normalize to the async driver in case a sync URL is supplied via env."""
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
