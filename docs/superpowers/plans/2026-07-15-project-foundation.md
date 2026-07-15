# Project Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (\`- [ ]\`) syntax for tracking.

**Goal:** Create a runnable, testable foundation for the Telegram AI SaaS service with validated configuration, a secure health endpoint, and local container dependencies.

**Architecture:** A modular monolith starts with a narrow core: settings and logging contain no Telegram or database logic; FastAPI exposes only liveness. PostgreSQL/pgvector and Redis run as separate Docker services, ready for later persistence and background jobs.

**Tech Stack:** Python 3.12, FastAPI, Pydantic Settings, Uvicorn, pytest, Ruff, Docker Compose, PostgreSQL 16 with pgvector, Redis 7.

## Global Constraints

- Python version is 3.12 or later.
- Secrets come only from environment variables and are never committed.
- Health responses reveal no settings, tokens, database addresses, or errors.
- Tests precede the implementation step they validate.
- Application code must retain the approved clean-architecture boundaries.
- Docker is local infrastructure only; production Nginx and VPS deployment are later modules.

---

## File Structure

- \`pyproject.toml\` — metadata, dependencies and test/lint configuration.
- \`src/app/core/config.py\` — immutable environment settings.
- \`src/app/core/logging.py\` — logging configuration.
- \`src/app/main.py\` — application factory and health route.
- \`tests/unit/core/test_config.py\` — settings tests.
- \`tests/integration/test_health.py\` — ASGI health tests.
- \`.env.example\` — safe variable template.
- \`Dockerfile\`, \`docker-compose.yml\`, \`.dockerignore\` — local runtime.
- \`README.md\` — local setup and verification commands.

### Task 1: Create the Python package and test harness

**Files:**
- Create: \`pyproject.toml\`, \`src/app/__init__.py\`, \`src/app/core/__init__.py\`, \`tests/__init__.py\`, \`tests/test_project_layout.py\`, \`README.md\`

**Interfaces:**
- Produces: importable \`app\` package; \`pytest\` and \`ruff check .\` commands.

- [ ] **Step 1: Write the failing layout test**

\`\`\`python
from pathlib import Path


def test_project_declares_python_312_or_newer() -> None:
    assert 'requires-python = ">=3.12"' in Path("pyproject.toml").read_text(
        encoding="utf-8"
    )


def test_app_package_exists() -> None:
    assert Path("src/app/__init__.py").is_file()
\`\`\`

- [ ] **Step 2: Verify failure**

Run: \`pytest tests/test_project_layout.py -v\`

Expected: FAIL because the project metadata and package do not yet exist.

- [ ] **Step 3: Implement minimal package metadata**

Create \`pyproject.toml\`:

\`\`\`toml
[build-system]
requires = ["hatchling>=1.27,<2"]
build-backend = "hatchling.build"

[project]
name = "telegram-ai-saas"
version = "0.1.0"
description = "Multi-tenant Telegram Business AI assistant"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115,<1",
  "pydantic-settings>=2.6,<3",
  "uvicorn[standard]>=0.30,<1",
]

[project.optional-dependencies]
dev = [
  "httpx>=0.27,<1",
  "pytest>=8.3,<9",
  "ruff>=0.8,<1",
]

[tool.hatch.build.targets.wheel]
packages = ["src/app"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-ra"

[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
\`\`\`

Create empty package marker files and a README containing:

\`\`\`text
python -m pip install -e .[dev]
pytest
ruff check .
\`\`\`

- [ ] **Step 4: Verify the package**

Run: \`pytest tests/test_project_layout.py -v && ruff check .\`

Expected: PASS and \`All checks passed!\`.

- [ ] **Step 5: Commit**

Run:

\`\`\`bash
git init
git add pyproject.toml src/app tests README.md
git commit -m "chore: initialize Python project"
\`\`\`

Expected: one repository commit.

### Task 2: Implement validated environment settings

**Files:**
- Create: \`src/app/core/config.py\`, \`tests/unit/core/__init__.py\`, \`tests/unit/core/test_config.py\`, \`.env.example\`

**Interfaces:**
- Produces: \`Settings\` and \`get_settings() -> Settings\`.
- Required settings: \`telegram_business_bot_token\`, \`telegram_access_bot_token\`.
- Defaults: development environment, INFO logging, PostgreSQL async URL and Redis URL.

- [ ] **Step 1: Write failing tests**

\`\`\`python
import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_have_safe_defaults() -> None:
    settings = Settings(
        telegram_business_bot_token="business-token",
        telegram_access_bot_token="access-token",
    )

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_settings_reject_empty_bot_token() -> None:
    with pytest.raises(ValidationError):
        Settings(
            telegram_business_bot_token="",
            telegram_access_bot_token="access-token",
        )
\`\`\`

- [ ] **Step 2: Verify failure**

Run: \`pytest tests/unit/core/test_config.py -v\`

Expected: FAIL with \`ModuleNotFoundError: No module named 'app.core.config'\`.

- [ ] **Step 3: Implement settings and variable template**

\`\`\`python
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://app:app@postgres:5432/app"
    redis_url: str = "redis://redis:6379/0"
    telegram_business_bot_token: SecretStr = Field(min_length=1)
    telegram_access_bot_token: SecretStr = Field(min_length=1)


@lru_cache
def get_settings() -> Settings:
    return Settings()
\`\`\`

Create \`.env.example\`:

\`\`\`dotenv
APP_ENV=development
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://app:app@postgres:5432/app
REDIS_URL=redis://redis:6379/0
TELEGRAM_BUSINESS_BOT_TOKEN=replace-me
TELEGRAM_ACCESS_BOT_TOKEN=replace-me
\`\`\`

- [ ] **Step 4: Verify implementation**

Run: \`pytest tests/unit/core/test_config.py -v && ruff check src/app/core/config.py tests/unit/core/test_config.py\`

Expected: PASS without printing either token.

- [ ] **Step 5: Commit**

\`\`\`bash
git add src/app/core/config.py tests/unit/core/test_config.py tests/unit/core/__init__.py .env.example
git commit -m "feat: add validated application settings"
\`\`\`

### Task 3: Add logging and a restricted health endpoint

**Files:**
- Create: \`src/app/core/logging.py\`, \`src/app/main.py\`, \`tests/integration/__init__.py\`, \`tests/integration/test_health.py\`

**Interfaces:**
- Produces: \`create_app() -> FastAPI\` and \`GET /healthz\`.
- The endpoint response must equal \`{"status": "ok"}\`.

- [ ] **Step 1: Write failing endpoint test**

\`\`\`python
from fastapi.testclient import TestClient

from app.main import create_app


def test_health_endpoint_returns_no_operational_details() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
\`\`\`

- [ ] **Step 2: Verify failure**

Run: \`pytest tests/integration/test_health.py -v\`

Expected: FAIL with \`ModuleNotFoundError: No module named 'app.main'\`.

- [ ] **Step 3: Implement logging and application factory**

\`\`\`python
# src/app/core/logging.py
import logging


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
\`\`\`

\`\`\`python
# src/app/main.py
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.logging import configure_logging


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title="Telegram AI SaaS", docs_url=None, redoc_url=None)

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
\`\`\`

- [ ] **Step 4: Verify application**

Run: \`pytest -v && ruff check .\`

Expected: PASS. The endpoint contains no secret or connection information.

- [ ] **Step 5: Commit**

\`\`\`bash
git add src/app/core/logging.py src/app/main.py tests/integration
git commit -m "feat: add application health endpoint"
\`\`\`

### Task 4: Add local Docker runtime

**Files:**
- Create: \`Dockerfile\`, \`docker-compose.yml\`, \`.dockerignore\`, \`tests/test_container_contract.py\`
- Modify: \`README.md\`

**Interfaces:**
- Produces: \`docker compose up --build\` with \`app\`, \`postgres\` and \`redis\`.
- Health verification: \`http://localhost:8000/healthz\`.

- [ ] **Step 1: Write failing Docker contract test**

\`\`\`python
from pathlib import Path


def test_compose_declares_required_services() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    for service in ("app:", "postgres:", "redis:"):
        assert service in compose


def test_dockerignore_excludes_environment_file() -> None:
    assert ".env" in Path(".dockerignore").read_text(encoding="utf-8")
\`\`\`

- [ ] **Step 2: Verify failure**

Run: \`pytest tests/test_container_contract.py -v\`

Expected: FAIL because Docker files do not exist.

- [ ] **Step 3: Implement container configuration**

\`\`\`dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN addgroup --system app && adduser --system --ingroup app app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
\`\`\`

\`\`\`yaml
services:
  app:
    build: .
    env_file: .env
    ports: ["8000:8000"]
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
  postgres:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: app
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U app -d app"]
      interval: 5s
      timeout: 3s
      retries: 10
  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10
\`\`\`

Create \`.dockerignore\` with \`.env\`, \`.git\`, Python caches, test caches, \`tests\` and \`docs\`. Add Docker start and health-check commands to README.

- [ ] **Step 4: Verify Docker contract and runtime**

Run:

\`\`\`bash
pytest tests/test_container_contract.py -v
docker compose config
docker compose up --build -d
curl --fail http://localhost:8000/healthz
docker compose down
\`\`\`

Expected: all tests pass, Compose validates, the health request returns \`{"status":"ok"}\`, and containers stop cleanly.

- [ ] **Step 5: Commit**

\`\`\`bash
git add Dockerfile docker-compose.yml .dockerignore README.md tests/test_container_contract.py
git commit -m "build: add local container runtime"
\`\`\`

## Plan Self-Review

- Spec coverage: safe configuration, logging, asynchronous-ready HTTP entry point, Docker dependencies, local verification and secret handling are covered. Telegram, persistence schema, RAG and approval workflows are later modules.
- Completeness scan: each task has named files, tests, implementation excerpts, commands and expected results.
- Type consistency: \`Settings\` precedes \`create_app\`; \`create_app\` is the endpoint test import; the module-level \`app\` is the Docker target.
