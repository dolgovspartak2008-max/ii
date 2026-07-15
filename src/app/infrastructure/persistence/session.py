"""Database engine and session factory creation."""

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine


def create_database_engine(database_url: str) -> AsyncEngine:
    """Create the application's asynchronous PostgreSQL engine."""
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker:
    """Create sessions that keep loaded values available after commits."""
    return async_sessionmaker(engine, expire_on_commit=False)
