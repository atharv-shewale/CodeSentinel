"""
CodeSentinel Core: Database Engine & Session Management.

Provides asynchronous SQLAlchemy database connection pooling and schema initialization.
"""

from __future__ import annotations

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
from app.core.logging import logger
from app.models.base import Base
# Import all models to ensure metadata registration
from app.models.project import ProjectModel
try:
    import app.audits.models
    import app.testing.models
    import app.failures.models
except ImportError:
    pass

_engine: Optional[AsyncEngine] = None
_session_factory: Optional[async_sessionmaker[AsyncSession]] = None


def get_database_url() -> str:
    """Retrieve active database URL from environment or settings."""
    env_url = os.environ.get("DATABASE_URL")
    if env_url:
        return env_url
    return settings.DATABASE_URL


def get_engine(db_url: Optional[str] = None) -> AsyncEngine:
    """Obtain or initialize the global AsyncEngine."""
    global _engine, _session_factory
    url = db_url or get_database_url()

    if _engine is None or db_url is not None:
        engine = create_async_engine(
            url,
            echo=False,
            future=True,
            pool_pre_ping=True,
        )
        if db_url is None:
            _engine = engine
            _session_factory = async_sessionmaker(
                bind=_engine,
                expire_on_commit=False,
                autocommit=False,
                autoflush=False,
            )
        return engine

    return _engine


def get_sessionmaker(db_url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    """Obtain or initialize async session factory."""
    global _session_factory
    if db_url is not None:
        engine = get_engine(db_url)
        return async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

    if _session_factory is None:
        get_engine()
    return _session_factory  # type: ignore


async def init_db(db_url: Optional[str] = None) -> None:
    """Create all registered database tables if they do not already exist."""
    engine = get_engine(db_url)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization encountered an error (continuing if tables exist): {e}")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for yielding transactional database sessions."""
    session_maker = get_sessionmaker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
