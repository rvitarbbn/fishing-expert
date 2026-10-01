"""Database service — supports PostgreSQL (production) and SQLite (local dev).

When ``DATABASE_URL`` starts with ``sqlite`` the async engine uses
``aiosqlite``; when it starts with ``postgresql`` it uses ``asyncpg``.
This lets developers run the API on Windows without Docker or Postgres.
"""

import logging
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
    pass


def get_async_database_url() -> str:
    """Convert the configured DATABASE_URL to an async dialect.

    * ``postgresql://…`` → ``postgresql+asyncpg://…``
    * ``sqlite:///…``    → ``sqlite+aiosqlite:///…``
    * Already async URLs are returned as-is.
    """
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    return url


_async_url = get_async_database_url()
_is_sqlite = _async_url.startswith("sqlite")

# SQLite does not support pool_pre_ping
_engine_kwargs: dict = {"echo": settings.api_debug}
if not _is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(_async_url, **_engine_kwargs)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables (auto-creates the SQLite file when needed)."""
    logger.info("Initializing database (%s)…", "SQLite" if _is_sqlite else "PostgreSQL")

    if _is_sqlite:
        # Ensure the directory for the SQLite file exists
        db_path = _async_url.split("sqlite+aiosqlite:///")[-1]
        if db_path:
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    async with engine.begin() as conn:
        # Import models to register them with Base.metadata
        from src.models import admin, feedback, recommendation  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
