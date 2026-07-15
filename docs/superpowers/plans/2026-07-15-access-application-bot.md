# Access Application Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task.

**Goal:** Implement a separate Telegram bot that accepts an application and lets the configured global administrator approve or reject it.

**Architecture:** Domain state transitions are independent of Telegram. Application use cases depend on repository and notification ports. SQLAlchemy implements PostgreSQL persistence; aiogram adapts commands, callbacks and webhook updates.

**Tech Stack:** Python 3.12, aiogram 3.29, SQLAlchemy 2, asyncpg, Alembic, FastAPI, PostgreSQL and pytest.

## Global Constraints

- All visible bot text is Russian.
- A Telegram user has one application with status pending, approved, rejected or blocked.
- Only ADMIN_TELEGRAM_ID can review an application.
- Duplicate updates cannot create duplicate applications or notifications.
- Tokens, database credentials and webhook secret stay in environment variables.

---

## File Structure

- src/app/domain/access/entities.py: application state and transitions.
- src/app/application/access/ports.py: repository and notification protocols.
- src/app/application/access/use_cases.py: submit, approve and reject workflows.
- src/app/infrastructure/persistence/models/access.py: SQLAlchemy records.
- src/app/infrastructure/persistence/repositories/access.py: PostgreSQL repository.
- src/app/infrastructure/telegram/access_bot/router.py: command and callback adapters.
- src/app/presentation/webhooks/access.py: protected FastAPI webhook.
- tests/unit/access and tests/integration/access: unit and integration coverage.

### Task 1: Domain application model

**Files:** Create domain access entity and ports; test tests/unit/access/test_access_application.py.

- [ ] **Step 1: Write failing tests**

```python
def test_pending_application_can_be_approved() -> None:
    application = AccessApplication.submit(telegram_id=42)
    application.approve()
    assert application.status is ApplicationStatus.APPROVED

def test_approved_application_cannot_be_rejected() -> None:
    application = AccessApplication.submit(telegram_id=42)
    application.approve()
    with pytest.raises(InvalidApplicationTransition):
        application.reject()
```

- [ ] **Step 2: Verify RED**

Run: python -m pytest tests/unit/access/test_access_application.py -v

- [ ] **Step 3: Implement**

Create ApplicationStatus as a string enum and AccessApplication dataclass with UUID, Telegram ID, status and transitions allowing only pending to approved or rejected. Define async repository and notification protocols.

- [ ] **Step 4: Verify GREEN**

Run: python -m pytest tests/unit/access/test_access_application.py -v

- [ ] **Step 5: Commit**

Run: git add src/app/domain/access src/app/application/access tests/unit/access; git commit -m "feat: add access application domain"

### Task 2: PostgreSQL persistence

**Files:** Modify pyproject.toml and environment template. Create database session, SQLAlchemy model, repository, Alembic migration and repository integration test.

- [ ] **Step 1: Write failing contract test**

```python
async def test_duplicate_submission_returns_existing_pending_application(repository) -> None:
    first = await repository.create_pending(telegram_id=42)
    second = await repository.create_pending(telegram_id=42)
    assert second.id == first.id
```

- [ ] **Step 2: Verify RED**

Run: python -m pytest tests/integration/access/test_access_repository.py -v

- [ ] **Step 3: Implement**

Add aiogram, SQLAlchemy, asyncpg and Alembic dependencies. Add access_applications table with unique telegram_id, status, timestamps, reviewer ID and version. Database uniqueness handles concurrent updates.

- [ ] **Step 4: Verify GREEN**

Run: docker compose up -d postgres; python -m pytest tests/integration/access/test_access_repository.py -v; docker compose down

- [ ] **Step 5: Commit**

Run: git add pyproject.toml src/app/infrastructure/persistence alembic tests/integration/access; git commit -m "feat: persist access applications"

### Task 3: Submit and review use cases

**Files:** Create use_cases.py and unit tests.

- [ ] **Step 1: Write failing tests**

```python
async def test_submit_notifies_admin_only_for_new_application() -> None:
    result = await submit.execute(telegram_id=42, username="client")
    assert result.is_new is True
```

```python
async def test_non_admin_cannot_approve() -> None:
    with pytest.raises(ForbiddenReviewer):
        await review.approve(application_id=application.id, reviewer_id=7)
```

- [ ] **Step 2: Verify RED**

Run: python -m pytest tests/unit/access/test_use_cases.py -v

- [ ] **Step 3: Implement**

Persist a new pending application before notifying the administrator. Check reviewer ID before state change. Persist approval or rejection before sending applicant notification. A failed notification creates an outbox event.

- [ ] **Step 4: Verify GREEN**

Run: python -m pytest tests/unit/access/test_use_cases.py -v

- [ ] **Step 5: Commit**

Run: git add src/app/application/access tests/unit/access; git commit -m "feat: add access review workflows"

### Task 4: Aiogram webhook interface

**Files:** Create callback parser, router and webhook route; modify main.py and config.py; create integration webhook test.

- [ ] **Step 1: Write failing tests**

```python
async def test_invalid_webhook_secret_returns_not_found(client) -> None:
    response = await client.post("/webhooks/access/wrong", json={"update_id": 1})
    assert response.status_code == 404
```

- [ ] **Step 2: Verify RED**

Run: python -m pytest tests/integration/access/test_access_webhook.py -v

- [ ] **Step 3: Implement**

Use an aiogram Router. Start command sends the Russian button Подать заявку. Callback data is parsed as access:approve:id and access:reject:id. Webhook route validates the configured secret and feeds updates to the dispatcher.

- [ ] **Step 4: Verify GREEN**

Run: python -m pytest tests/integration/access/test_access_webhook.py -v; python -m ruff check .

- [ ] **Step 5: Commit**

Run: git add src/app/infrastructure/telegram/access_bot src/app/presentation/webhooks src/app/main.py src/app/core/config.py tests/integration/access; git commit -m "feat: add access application bot webhook"

## Plan Self-Review

- Coverage includes Russian application submission, global manual review, PostgreSQL persistence, update deduplication and secret-protected webhook.
- Interfaces flow domain to application to infrastructure; Telegram types do not enter domain or use cases.
