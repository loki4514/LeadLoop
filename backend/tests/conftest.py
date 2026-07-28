"""Shared fixtures.

`db` gives each test a fresh in-memory SQLite database with just the tables the
assignment logic touches (employees, leads, assignments). We create those tables
explicitly rather than `Base.metadata.create_all()` because other models (e.g.
Document) use a pgvector column type SQLite can't build.
"""
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.assignment import Assignment
from app.models.employee import Employee
from app.models.lead import Lead


@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    tables = [m.__table__ for m in (Employee, Lead, Assignment)]
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, tables=tables))

    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session

    await engine.dispose()
