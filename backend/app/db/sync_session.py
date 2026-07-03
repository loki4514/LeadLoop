"""Synchronous DB session for the RQ worker.

RQ jobs run synchronously, so the ingestion job uses a plain (psycopg2) engine
rather than the async engine the FastAPI app uses.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings


def _sync_url() -> str:
    url = settings.DATABASE_URL
    # Normalize any async driver back to a sync psycopg2 URL.
    if "+asyncpg" in url:
        url = url.replace("+asyncpg", "")
    if url.startswith("postgresql+"):
        url = "postgresql://" + url.split("://", 1)[1]
    elif url.startswith("postgresql://"):
        pass
    return url


_engine = None
_SessionLocal = None


def _get_sessionmaker():
    """Build the engine/sessionmaker lazily so importing this module never
    requires a live DB or the psycopg2 driver until a job actually runs."""
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = create_engine(_sync_url(), pool_pre_ping=True)
        _SessionLocal = sessionmaker(
            bind=_engine, class_=Session, expire_on_commit=False
        )
    return _SessionLocal


def SyncSessionLocal() -> Session:
    """Open a new synchronous session (matches the callable usage in jobs)."""
    return _get_sessionmaker()()
