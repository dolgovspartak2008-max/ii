# Tenant Onboarding and Business Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let an approved Telegram owner create exactly one isolated business tenant and maintain the business context used by the main bot.

**Architecture:** The domain owns tenant invariants; an application service turns an approved access application into a tenant idempotently. PostgreSQL enforces one tenant per owner and keeps all business settings behind `tenant_id`. The main bot exposes Russian owner-only commands and never lets one owner read or alter another tenant.

**Tech Stack:** Python 3.12, aiogram 3.29, FastAPI, SQLAlchemy 2, asyncpg, Alembic, PostgreSQL, pytest and Ruff.

## Global Constraints

- One approved owner has at most one tenant and one business profile in MVP.
- Every business record is addressed by `tenant_id`; cross-tenant reads and writes are forbidden.
- The main bot UI is Russian; access applications stay in the separate access bot.
- A non-approved Telegram user cannot create or configure a tenant.
- Telegram and database failures must not expose data from another tenant.
- Tests are written and observed failing before production changes.

---

## File Structure

- `src/app/domain/tenants/entities.py` — tenant and business-profile value objects.
- `src/app/application/tenants/ports.py` — tenant, approval and notification contracts.
- `src/app/application/tenants/use_cases.py` — idempotent onboarding and profile updates.
- `src/app/infrastructure/persistence/models/tenants.py` — SQLAlchemy tenant tables.
- `src/app/infrastructure/persistence/repositories/tenants.py` — PostgreSQL tenant repository.
- `src/app/infrastructure/telegram/business_bot/router.py` — owner commands in the main bot.
- `src/app/main.py` — composition of the main-bot dispatcher and its protected webhook.
- `tests/unit/tenants/` and `tests/integration/tenants/` — isolation and persistence coverage.

### Task 1: Define tenant invariants

**Files:**
- Create: `src/app/domain/tenants/__init__.py`, `src/app/domain/tenants/entities.py`, `tests/unit/tenants/__init__.py`, `tests/unit/tenants/test_entities.py`

**Interfaces:**
- Produces `Tenant.create(owner_telegram_id: int) -> Tenant` and `BusinessProfile.update(name: str, description: str) -> None`.
- `Tenant` exposes `id: UUID` and `owner_telegram_id: int`; both profile strings must be non-empty after trimming.

- [ ] **Step 1: Write the failing domain tests**

```python
import pytest

from app.domain.tenants.entities import BusinessProfile, InvalidBusinessProfile, Tenant


def test_tenant_belongs_to_exactly_one_owner() -> None:
    tenant = Tenant.create(owner_telegram_id=42)
    assert tenant.owner_telegram_id == 42


def test_profile_rejects_blank_business_name() -> None:
    with pytest.raises(InvalidBusinessProfile):
        BusinessProfile.create(name="   ", description="Описание")
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/unit/tenants/test_entities.py -v`

Expected: import failure because the tenant domain does not exist.

- [ ] **Step 3: Implement the domain objects**

```python
@dataclass(frozen=True)
class Tenant:
    id: UUID
    owner_telegram_id: int

    @classmethod
    def create(cls, owner_telegram_id: int) -> "Tenant":
        if owner_telegram_id <= 0:
            raise ValueError("Owner Telegram ID must be positive.")
        return cls(id=uuid4(), owner_telegram_id=owner_telegram_id)
```

Implement `BusinessProfile.create` and `update` with stripped values and `InvalidBusinessProfile` for blank names or descriptions.

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/unit/tenants/test_entities.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit**

Run: `git add src/app/domain/tenants tests/unit/tenants && git commit -m "feat: add tenant domain"`

### Task 2: Persist tenants and business profiles with database constraints

**Files:**
- Create: `src/app/infrastructure/persistence/models/tenants.py`, `src/app/infrastructure/persistence/repositories/tenants.py`, `alembic/versions/20260716_03_create_tenants.py`, `tests/integration/tenants/test_tenant_repository.py`
- Modify: `alembic/env.py`

**Interfaces:**
- Produces `PostgresTenantRepository.create_for_owner(owner_telegram_id: int) -> TenantCreation`.
- `TenantCreation` contains `tenant: Tenant` and `is_new: bool`.
- Produces `update_business_profile(tenant_id: UUID, name: str, description: str) -> BusinessProfile`.

- [ ] **Step 1: Write the failing persistence test**

```python
async def scenario() -> None:
    first = await repository.create_for_owner(owner_telegram_id=42)
    second = await repository.create_for_owner(owner_telegram_id=42)
    assert first.tenant.id == second.tenant.id
    assert first.is_new is True
    assert second.is_new is False
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest -q tests/integration/tenants/test_tenant_repository.py`

Expected: import failure because the repository does not exist.

- [ ] **Step 3: Implement schema, migration and repository**

Create `tenants` with `id UUID PRIMARY KEY`, `owner_telegram_id BIGINT UNIQUE NOT NULL`, timestamps and active status. Create `business_profiles` with `tenant_id UUID UNIQUE REFERENCES tenants(id)`, `name`, `description` and `updated_at`. Use PostgreSQL `INSERT ... ON CONFLICT DO NOTHING ... RETURNING` to return the one tenant for an owner without a race.

```python
async def create_for_owner(self, owner_telegram_id: int) -> TenantCreation:
    statement = insert(TenantModel).values(owner_telegram_id=owner_telegram_id)
    statement = statement.on_conflict_do_nothing(
        index_elements=[TenantModel.owner_telegram_id]
    ).returning(TenantModel)
```

Add the model import to Alembic metadata and create migration revision `20260716_03` with the unique constraints.

- [ ] **Step 4: Verify GREEN**

Run: `python -m alembic upgrade head; python -m pytest -q tests/integration/tenants/test_tenant_repository.py`

Expected: migration reaches `20260716_03 (head)` and the test passes.

- [ ] **Step 5: Commit**

Run: `git add alembic src/app/infrastructure/persistence tests/integration/tenants && git commit -m "feat: persist isolated tenants"`

### Task 3: Onboard approved owners and configure a business profile

**Files:**
- Create: `src/app/application/tenants/__init__.py`, `src/app/application/tenants/ports.py`, `src/app/application/tenants/use_cases.py`, `tests/unit/tenants/test_use_cases.py`

**Interfaces:**
- Produces `OnboardApprovedOwner.execute(owner_telegram_id: int) -> TenantCreation`.
- Produces `UpdateBusinessProfile.execute(owner_telegram_id: int, name: str, description: str) -> BusinessProfile`.
- Raises `OwnerNotApproved` for missing or non-approved access applications and `TenantNotFound` for an owner without onboarding.

- [ ] **Step 1: Write the failing use-case tests**

```python
async def test_onboarding_rejects_an_unapproved_owner() -> None:
    with pytest.raises(OwnerNotApproved):
        await onboarding.execute(owner_telegram_id=42)


async def test_owner_can_update_only_own_business_profile() -> None:
    profile = await update.execute(42, "Кофейня", "Кофе и десерты")
    assert profile.name == "Кофейня"
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/unit/tenants/test_use_cases.py -v`

Expected: import failure because tenant application services do not exist.

- [ ] **Step 3: Implement ports and workflows**

Define an `AccessApprovalPort` that retrieves an access application by Telegram ID and a `TenantRepository` that never accepts a caller-supplied tenant id for owner operations. `OnboardApprovedOwner` checks `ApplicationStatus.APPROVED` before creating a tenant. `UpdateBusinessProfile` resolves the tenant by owner id, validates through `BusinessProfile`, then persists only that tenant's row.

```python
if application is None or application.status is not ApplicationStatus.APPROVED:
    raise OwnerNotApproved("Owner must have an approved access application.")
tenant = await self._tenants.get_by_owner(owner_telegram_id)
if tenant is None:
    raise TenantNotFound("Owner has not completed onboarding.")
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest tests/unit/tenants/test_use_cases.py -v`

Expected: approved onboarding is idempotent; unapproved owners and cross-owner updates are denied.

- [ ] **Step 5: Commit**

Run: `git add src/app/application/tenants tests/unit/tenants && git commit -m "feat: add approved owner onboarding"`

### Task 4: Expose Russian owner setup commands in the main bot

**Files:**
- Create: `src/app/infrastructure/telegram/business_bot/__init__.py`, `src/app/infrastructure/telegram/business_bot/router.py`, `tests/integration/tenants/test_business_router.py`
- Modify: `src/app/main.py`, `.env.example`, `tests/integration/test_health.py`

**Interfaces:**
- Produces `create_business_router(onboard: OnboardApprovedOwner, update: UpdateBusinessProfile) -> Router`.
- `/start` creates or opens the approved owner's tenant; `/business <name> | <description>` saves that owner's business context.
- The main-bot webhook path is `/webhooks/business/{secret}` and uses a separate `TELEGRAM_BUSINESS_WEBHOOK_SECRET` setting.

- [ ] **Step 1: Write failing adapter tests**

```python
def test_business_webhook_is_not_the_access_webhook() -> None:
    assert "/webhooks/business/" in app_routes


async def test_non_approved_start_returns_russian_access_message() -> None:
    await router_handler(message_from(telegram_id=42, text="/start"))
    assert sent_text == "Сначала подайте заявку через отдельный бот доступа."
```

- [ ] **Step 2: Verify RED**

Run: `python -m pytest tests/integration/tenants/test_business_router.py -v`

Expected: failure because the main-bot router and webhook are absent.

- [ ] **Step 3: Implement the main-bot adapter and composition**

Use aiogram `CommandStart` and `Command("business")`. Parse `/business` only around a single `|`; return a Russian format hint if either field is absent. Map `OwnerNotApproved` to the separate-access-bot message and do not reveal review details. Add a new protected webhook router factory that follows the same constant-time secret comparison as the access webhook, while keeping the access dispatcher separate.

```python
@router.message(Command("business"))
async def save_business(message: Message, command: CommandObject) -> None:
    name, separator, description = (command.args or "").partition("|")
    if not separator:
        await message.answer("Формат: /business Название | Чем занимается бизнес")
        return
    await update.execute(message.from_user.id, name, description)
```

- [ ] **Step 4: Verify GREEN**

Run: `python -m pytest -q --disable-warnings; python -m ruff check .; python -m alembic current`

Expected: full suite passes, lint is clean, and the database reports revision `20260716_03 (head)`.

- [ ] **Step 5: Commit**

Run: `git add src/app/main.py src/app/infrastructure/telegram/business_bot src/app/core/config.py .env.example tests && git commit -m "feat: add owner business setup"`

## Plan Self-Review

- Coverage: approved-only onboarding, one-owner/one-tenant enforcement, `tenant_id` data isolation, Russian owner settings, and distinct webhook secrets are covered by Tasks 1–4.
- No placeholders: every task names its files, concrete public interfaces, tests, implementation behavior, and verification commands.
- Scope: Telegram Business connected-chat events, AI replies, RAG, exclusions and usage metering remain independent later modules and are intentionally not coupled into tenant onboarding.
