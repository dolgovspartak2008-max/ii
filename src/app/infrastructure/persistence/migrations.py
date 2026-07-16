"""Runtime configuration helpers for Alembic migrations."""

import os


def migration_database_url(fallback_url: str) -> str:
    """Use the deployed database URL when Alembic is started in a container."""
    return os.getenv("DATABASE_URL", fallback_url)
