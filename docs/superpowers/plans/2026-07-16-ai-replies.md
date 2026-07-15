# Tenant AI Replies Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reply to customer Telegram Business messages with an OpenRouter model using only that tenant's business profile.

**Architecture:** A small application service decides whether a tenant chat is eligible, then invokes an `AIResponder` port. The OpenRouter adapter owns HTTP/authentication and the Business event handler delivers a prefixed response through the same Business connection. Provider errors are deliberately invisible to customers.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, httpx, pytest.

## Global Constraints

- Every query and prompt is scoped by the server-side tenant ID.
- The model is configured with `OPENROUTER_API_KEY` and `OPENROUTER_MODEL`; no key is logged or committed.
- Reply only to text messages in `ACTIVE` chats; an owner message keeps the chat in human handoff.
- Customer-facing AI replies start with `ИИ:`; provider failures send no reply.

---

### Task 1: AI reply service and tenant chat lookup

**Files:**
- Create: `src/app/application/ai/ports.py`
- Create: `src/app/application/ai/use_cases.py`
- Modify: `src/app/infrastructure/persistence/repositories/chats.py`
- Test: `tests/unit/ai/test_use_cases.py`

- [x] Write failing tests for active-chat generation and handoff/profile skips.
- [x] Add `get_customer_chat(tenant_id, telegram_chat_id)` and an `AIResponder` protocol.
- [x] Implement `GenerateBusinessReply.execute(tenant_id, chat_id, customer_text)` returning a prefixed reply or `None`.
- [x] Run `pytest tests/unit/ai/test_use_cases.py -q`.
- [x] Commit the tested application boundary.

### Task 2: OpenRouter adapter and configuration

**Files:**
- Create: `src/app/infrastructure/ai/openrouter.py`
- Modify: `src/app/core/config.py`
- Modify: `.env.example`
- Test: `tests/unit/ai/test_openrouter.py`

- [x] Write failing HTTP-transport tests for request shape, response extraction, and provider errors.
- [x] Add settings and a timeout-bound OpenAI-compatible OpenRouter client without logging credentials.
- [x] Run `pytest tests/unit/ai/test_openrouter.py -q`.
- [x] Commit the provider adapter.

### Task 3: Telegram Business delivery and composition

**Files:**
- Modify: `src/app/infrastructure/telegram/business_bot/events.py`
- Modify: `src/app/main.py`
- Modify: `tests/unit/chats/test_events.py`
- Modify: `tests/integration/test_health.py`

- [x] Write failing handler tests proving text customer messages are delivered with the connection ID and owner/non-text messages are not generated.
- [x] Inject the service and bot into the event router, then compose OpenRouter in the ASGI application.
- [x] Run focused tests, full `pytest -q --disable-warnings`, and `ruff check .`.
- [ ] Commit, merge the isolated branch, push `main`, and verify the configured provider without printing its key.
