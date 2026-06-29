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

    # Optional (used later by the agent/worker)
    ANTHROPIC_API_KEY: str = ""

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
