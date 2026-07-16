from app.infrastructure.persistence.migrations import migration_database_url


def test_migration_database_url_prefers_runtime_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://remote.example/app")

    url = migration_database_url("postgresql+asyncpg://localhost/app")

    assert url == "postgresql+asyncpg://remote.example/app"


def test_migration_database_url_uses_fallback_without_runtime_value(
    monkeypatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    url = migration_database_url("postgresql+asyncpg://localhost/app")

    assert url == "postgresql+asyncpg://localhost/app"
