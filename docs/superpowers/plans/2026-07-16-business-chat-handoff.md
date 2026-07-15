# Telegram Business Chat Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist official Telegram Business connections and keep every customer chat in either AI-active or owner-managed state.

**Architecture:** A tenant can have one active Business connection. Incoming Business messages resolve their tenant through the connection id; owner-originated messages atomically change that customer chat to `human_handoff`. No LLM call is made in this stage.

**Tech Stack:** Python 3.12, aiogram 3.29, SQLAlchemy 2, Alembic, PostgreSQL, pytest and Ruff.

## Global Constraints

- `business_connection_id` maps to exactly one tenant while enabled.
- Customer chats use the unique pair `(tenant_id, telegram_chat_id)`.
- A manual owner message disables AI replies for that customer chat until a later explicit resume feature.
- Business updates never create tenant records and never infer a tenant from a customer id.

### Task 1: Domain state and persistence

**Files:** Create `src/app/domain/chats/entities.py`, `src/app/infrastructure/persistence/models/chats.py`, `src/app/infrastructure/persistence/repositories/chats.py`, migration `20260716_04_create_business_chats.py`, and integration tests.

- [ ] Write a failing test that stores one enabled connection per tenant, opens an `active` chat, and changes it to `human_handoff`.
- [ ] Run `python -m pytest -q tests/integration/chats/test_chat_repository.py` and observe the missing repository failure.
- [ ] Implement `ChatState`, `BusinessConnection`, and `CustomerChat`; create `business_connections` and `customer_chats` with unique constraints. Repository methods are `upsert_connection`, `get_connection`, `open_customer_chat`, and `mark_human_handoff`.
- [ ] Run migration and the focused test; commit `feat: persist business chat handoff`.

### Task 2: Telegram Business event adapter

**Files:** Create `src/app/infrastructure/telegram/business_bot/events.py`, unit tests, and modify `src/app/main.py`.

- [ ] Write a failing unit test for `is_owner_message(owner_id, sender_id)` and an event-dispatcher test that does not mutate an unknown connection.
- [ ] Run focused tests and observe the missing adapter failure.
- [ ] Register handlers for `business_connection` and `business_message`. Persist enabled connections; open active customer chats only for inbound messages; set `human_handoff` when the sender equals the connection owner.
- [ ] Run `python -m pytest -q --disable-warnings`, `python -m ruff check .`, and `python -m alembic current`; commit `feat: handle business chat handoff`.

### Task 3: Verification and delivery

- [ ] Run Docker build, start the service, check `/healthz`, then run migrations against a fresh PostgreSQL container.
- [ ] Merge the verified branch into `main`, rerun all tests, and push `main` to GitHub.

## Plan Self-Review

- Covers connection-to-tenant isolation, chat uniqueness, handoff transition and official Business event wiring.
- Defers AI generation, exclusions, knowledge search and explicit resume controls to later independent modules.
