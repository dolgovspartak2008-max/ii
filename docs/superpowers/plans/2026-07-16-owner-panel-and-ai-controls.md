# Owner Panel and AI Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give each approved Telegram owner a button-based management panel and let them enable or disable tenant AI replies.

**Architecture:** Persist one `ai_enabled` flag per tenant. The reply service checks that flag before contacting the provider. The business-bot router supplies inline controls and a two-step aiogram FSM wizard for the business profile. A reserved provider response token is mapped to a stable Russian clarification request.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, Alembic, pytest and Ruff.

## Global Constraints

- Every owner action resolves the tenant from `message.from_user.id`; callback data never carries a tenant ID.
- The customer sees the fixed clarification text, never the internal token.
- A manual owner reply keeps the existing `human_handoff` behavior.
- The panel is available only in the main Telegram bot; no web UI is added.

---

### Task 1: Persist and enforce the tenant AI switch

**Files:**
- Modify: `src/app/infrastructure/persistence/models/tenants.py`
- Modify: `src/app/infrastructure/persistence/repositories/tenants.py`
- Modify: `src/app/application/tenants/ports.py`
- Modify: `src/app/application/tenants/use_cases.py`
- Modify: `src/app/application/ai/use_cases.py`
- Create: `alembic/versions/20260716_05_add_tenant_ai_enabled.py`
- Test: `tests/unit/ai/test_use_cases.py`, `tests/unit/tenants/test_use_cases.py`

**Interfaces:**
- `TenantPort.set_ai_enabled(tenant_id: UUID, enabled: bool) -> bool`
- `TenantPort.is_ai_enabled(tenant_id: UUID) -> bool`
- `SetTenantAIEnabled.execute(owner_telegram_id: int, enabled: bool) -> bool`

- [ ] Add failing tests that a disabled tenant does not call the responder and an owner toggle resolves only that owner’s tenant.
- [ ] Run the focused tests and confirm they fail because the methods do not exist.
- [ ] Add `ai_enabled BOOLEAN NOT NULL DEFAULT true`, migration `20260716_05`, repository methods, application use case and reply-service guard.
- [ ] Run the focused tests and confirm they pass.

### Task 2: Return a stable clarification request for uncertain answers

**Files:**
- Modify: `src/app/application/ai/use_cases.py`
- Modify: `src/app/infrastructure/ai/openrouter.py`
- Test: `tests/unit/ai/test_use_cases.py`, `tests/unit/ai/test_openrouter.py`

**Interfaces:**
- `NEEDS_REPHRASE_TOKEN = "[[NEEDS_REPHRASE]]"`
- `CLARIFICATION_TEXT = "Извините, я не понял вопрос. Пожалуйста, переформулируйте его или уточните детали."`

- [ ] Add a failing unit test that maps the token to the clarification text without an `ИИ:` prefix.
- [ ] Run the focused test and confirm the current code returns the raw token.
- [ ] Require the exact token in the provider system prompt for ambiguous, unrelated or unsupported questions and map it in `GenerateBusinessReply`.
- [ ] Run focused tests and confirm they pass.

### Task 3: Add the owner’s inline Telegram panel and profile wizard

**Files:**
- Create: `src/app/infrastructure/telegram/business_bot/callbacks.py`
- Modify: `src/app/infrastructure/telegram/business_bot/router.py`
- Modify: `src/app/main.py`
- Test: `tests/unit/tenants/test_business_router.py`

**Interfaces:**
- `OwnerPanelCallback(action: Literal["show", "edit", "toggle_ai", "help", "cancel"])`
- `create_business_router(onboarding, update_profile, set_ai_enabled, tenants) -> Router`
- `/start` and `/admin` render the inline panel.

- [ ] Add failing tests for callback pack/unpack, panel labels and profile input validation.
- [ ] Run the focused test and confirm the callback import fails.
- [ ] Implement the callback type, inline keyboard, overview/help callbacks, global toggle and two-step FSM profile edit with save/cancel buttons.
- [ ] Run focused tests and confirm they pass.

### Task 4: Verify migration and runtime composition

**Files:**
- Modify: `tests/integration/test_health.py`
- Test: `tests/unit/ai/test_use_cases.py`, `tests/unit/tenants/test_business_router.py`, `tests/unit/chats/test_events.py`

- [ ] Add a failing composition test confirming the main router receives the AI-toggle use case.
- [ ] Run it and confirm the missing dependency failure.
- [ ] Compose the new use case in `create_app` and run all focused tests.
- [ ] Run `python -m pytest -q --disable-warnings` and `python -m ruff check .`; separately record any failures caused by an unavailable local PostgreSQL.

## Plan Self-Review

- The four tasks cover the approved panel, two-step profile editing, global AI control and the specified clarification response.
- Tenant IDs remain server-resolved and are not placed in callback payloads.
- No RAG, chat-resume controls or web UI are included because they are outside the requested scope.
