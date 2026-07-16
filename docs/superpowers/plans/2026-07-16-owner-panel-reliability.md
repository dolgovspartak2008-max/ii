# Owner Panel Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the main bot's owner panel reliably available through `/start` and `/admin`, provide chat handoff controls, and replace leaked uncertainty markers with customer-safe text.

**Architecture:** Keep authorization server-side: a use case resolves the callback sender to their tenant before it lists or resumes chats. The Telegram router owns presentation, state reset and command UX; persistence owns tenant-scoped chat transitions. The AI use case normalizes only the provider's reserved marker before applying the regular customer reply prefix.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, PostgreSQL, pytest and Ruff.

## Global Constraints

- `/start` and `/admin` clear abandoned edit state and open the same panel for an approved owner.
- All owner actions resolve a tenant from `message.from_user.id` or `callback.from_user.id`; callbacks never carry tenant IDs.
- A callback chat identifier is always combined with the server-resolved tenant for persistence operations.
- Only an exact normalized `[[NEEDS_REPHRASE]]` provider response becomes the fixed Russian clarification text.
- Existing skipped-reply behavior remains unchanged for provider failures, empty replies, missing profiles, disabled tenants and handed-off chats.
- No database migration is required; `customer_chats.state` already stores `active` and `human_handoff`.

---

## File Structure

- `src/app/application/chats/ports.py` — protocol for tenant-scoped chat management.
- `src/app/application/chats/use_cases.py` — owner-safe list and resume workflows.
- `src/app/infrastructure/persistence/repositories/chats.py` — PostgreSQL implementations of handoff listing and resume.
- `src/app/infrastructure/telegram/business_bot/callbacks.py` — owner panel actions and chat-id callback payload.
- `src/app/infrastructure/telegram/business_bot/router.py` — commands, panel rendering, profile wizard and chat controls.
- `src/app/infrastructure/telegram/webhooks.py` — main-bot command menu registration.
- `src/app/main.py` — compose chat use cases into the owner router.
- `src/app/application/ai/use_cases.py` — normalize the uncertainty marker before customer delivery.
- Tests under `tests/unit/` — test every new public behavior without requiring PostgreSQL.

### Task 1: Normalize the provider uncertainty marker

**Files:**
- Modify: `src/app/application/ai/use_cases.py`
- Modify: `tests/unit/ai/test_use_cases.py`

**Interfaces:**
- Produces `is_needs_rephrase_response(answer: str) -> bool`.
- `GenerateBusinessReply.execute(...) -> str | None` returns `CLARIFICATION_TEXT` when the normalized provider output is the reserved marker.

- [ ] **Step 1: Write failing tests for prefixed and formatted markers**

```python
@pytest.mark.asyncio
@pytest.mark.parametrize("answer", ["ИИ: [[NEEDS_REPHRASE]]", "`[[NEEDS_REPHRASE]]`"])
async def test_uncertainty_marker_variants_become_clarification(answer: str) -> None:
    tenant_id = uuid4()
    service = GenerateBusinessReply(
        FakeTenants(BusinessProfile.create("Кофейня", "Кофе с собой")),
        FakeChats(CustomerChat(tenant_id, 100, ChatState.ACTIVE)),
        FakeResponder(answer),
    )

    assert await service.execute(tenant_id, 100, "Непонятный вопрос") == CLARIFICATION_TEXT
```

- [ ] **Step 2: Run the focused test to verify RED**

Run: `python -m pytest -q tests/unit/ai/test_use_cases.py::test_uncertainty_marker_variants_become_clarification`

Expected: the `ИИ:`-prefixed and code-formatted forms fail because current equality checks only the raw token.

- [ ] **Step 3: Implement the minimal normalizer**

```python
def is_needs_rephrase_response(answer: str) -> bool:
    normalized = answer.strip()
    if normalized.startswith("ИИ:"):
        normalized = normalized.removeprefix("ИИ:").strip()
    if normalized.startswith("`") and normalized.endswith("`"):
        normalized = normalized[1:-1].strip()
    return normalized == NEEDS_REPHRASE_TOKEN
```

Replace `if answer == NEEDS_REPHRASE_TOKEN:` with the helper call and retain the existing reply-prefix code.

- [ ] **Step 4: Run the AI use-case tests to verify GREEN**

Run: `python -m pytest -q tests/unit/ai/test_use_cases.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the completed task**

```bash
git add src/app/application/ai/use_cases.py tests/unit/ai/test_use_cases.py
git commit -m "fix(ai): hide formatted uncertainty markers"
```

### Task 2: Add owner-safe handed-off chat workflows

**Files:**
- Create: `src/app/application/chats/__init__.py`
- Create: `src/app/application/chats/ports.py`
- Create: `src/app/application/chats/use_cases.py`
- Modify: `src/app/application/tenants/ports.py`
- Modify: `src/app/infrastructure/persistence/repositories/chats.py`
- Modify: `tests/unit/chats/test_events.py`
- Create: `tests/unit/chats/test_use_cases.py`

**Interfaces:**
- `ChatManagementPort.list_handoff_chats(tenant_id: UUID, limit: int = 10) -> list[CustomerChat]`
- `ChatManagementPort.resume_ai(tenant_id: UUID, telegram_chat_id: int) -> bool`
- `ListOwnerHandoffChats.execute(owner_telegram_id: int) -> list[CustomerChat]`
- `ResumeOwnerChatAI.execute(owner_telegram_id: int, telegram_chat_id: int) -> bool`

- [ ] **Step 1: Write failing use-case tests for tenant resolution**

```python
@pytest.mark.asyncio
async def test_owner_lists_only_own_handoff_chats() -> None:
    tenants = FakeTenants.with_owner(42)
    chats = FakeChats([CustomerChat(tenants.tenant.id, 700, ChatState.HUMAN_HANDOFF)])

    result = await ListOwnerHandoffChats(tenants, chats).execute(42)

    assert result == [CustomerChat(tenants.tenant.id, 700, ChatState.HUMAN_HANDOFF)]
    assert chats.listed_tenant_ids == [tenants.tenant.id]


@pytest.mark.asyncio
async def test_owner_cannot_resume_a_chat_outside_own_tenant() -> None:
    tenants = FakeTenants.with_owner(42)
    chats = FakeChats([])

    assert await ResumeOwnerChatAI(tenants, chats).execute(42, 700) is False
```

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python -m pytest -q tests/unit/chats/test_use_cases.py`

Expected: import failure because the chat-management application package does not exist.

- [ ] **Step 3: Implement protocols, use cases and repository methods**

```python
class ListOwnerHandoffChats:
    async def execute(self, owner_telegram_id: int) -> list[CustomerChat]:
        tenant = await self._tenants.get_by_owner(owner_telegram_id)
        if tenant is None:
            raise TenantNotFound("Owner has not completed onboarding.")
        return await self._chats.list_handoff_chats(tenant.id)


class ResumeOwnerChatAI:
    async def execute(self, owner_telegram_id: int, telegram_chat_id: int) -> bool:
        tenant = await self._tenants.get_by_owner(owner_telegram_id)
        if tenant is None:
            raise TenantNotFound("Owner has not completed onboarding.")
        return await self._chats.resume_ai(tenant.id, telegram_chat_id)
```

Implement `list_handoff_chats` with `tenant_id`, `state == human_handoff`, ascending `created_at`, and `limit`. Implement `resume_ai` as an `UPDATE` constrained by `tenant_id`, `telegram_chat_id`, and `human_handoff`, returning `False` if no row changes.

- [ ] **Step 4: Write and run repository statement tests**

Add a capturing-session test that compiles the resume statement and asserts it constrains `tenant_id`, `telegram_chat_id` and `state`. Run:

```bash
python -m pytest -q tests/unit/chats/test_use_cases.py tests/unit/chats/test_events.py
```

Expected: all chat unit tests pass.

- [ ] **Step 5: Commit the completed task**

```bash
git add src/app/application/chats src/app/application/tenants/ports.py src/app/infrastructure/persistence/repositories/chats.py tests/unit/chats
git commit -m "feat(chats): add owner handoff controls"
```

### Task 3: Make the owner panel resilient and actionable

**Files:**
- Modify: `src/app/infrastructure/telegram/business_bot/callbacks.py`
- Modify: `src/app/infrastructure/telegram/business_bot/router.py`
- Modify: `tests/unit/tenants/test_business_router.py`

**Interfaces:**
- `OwnerPanelCallback.action` adds `chats` and `back`.
- `OwnerChatCallback(CallbackData, prefix="owner-chat")` has `action: Literal["resume"]` and `telegram_chat_id: int`.
- `create_business_router(..., handoffs: ListOwnerHandoffChats, resume: ResumeOwnerChatAI) -> Router`.

- [ ] **Step 1: Write failing router helper tests**

```python
def test_owner_chat_callback_round_trip() -> None:
    callback = OwnerChatCallback.unpack(
        OwnerChatCallback(action="resume", telegram_chat_id=700).pack()
    )
    assert callback.telegram_chat_id == 700


def test_owner_panel_has_handoff_chat_button() -> None:
    keyboard = create_owner_panel_keyboard(ai_enabled=True)
    labels = [button.text for row in keyboard.inline_keyboard for button in row]
    assert "💬 Диалоги у вас" in labels
```

- [ ] **Step 2: Run focused test to verify RED**

Run: `python -m pytest -q tests/unit/tenants/test_business_router.py`

Expected: import failure because `OwnerChatCallback` and the chat button do not exist.

- [ ] **Step 3: Implement the panel and explicit command path**

Use distinct `/start` and `/admin` handlers that call one `open_owner_panel` helper. The helper clears `FSMContext`, calls onboarding idempotently, renders the dashboard, and maps `OwnerNotApproved` to `ACCESS_REQUIRED_TEXT`. The `/admin` handler is therefore not dependent on an old callback or profile-edit state.

Add chat-list and resume handlers. The list uses `handoffs.execute(callback.from_user.id)` and displays `Нет диалогов, переданных вам.` when empty. Every listed chat has a `Передать ИИ` callback created with `OwnerChatCallback`; the resume handler invokes `resume.execute(callback.from_user.id, callback_data.telegram_chat_id)` and never directly calls a repository. Add `Назад` to return to the current dashboard.

After saving a profile, toggling AI, cancelling an edit, or resuming AI, render a fresh panel. Catch `TenantNotFound` in every dashboard-derived callback and answer with `Сначала откройте панель командой /start.`.

- [ ] **Step 4: Run router unit tests to verify GREEN**

Run: `python -m pytest -q tests/unit/tenants/test_business_router.py tests/unit/tenants/test_use_cases.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the completed task**

```bash
git add src/app/infrastructure/telegram/business_bot tests/unit/tenants/test_business_router.py
git commit -m "feat(owner): improve management panel"
```

### Task 4: Register the command menu and compose the new services

**Files:**
- Modify: `src/app/infrastructure/telegram/webhooks.py`
- Modify: `src/app/main.py`
- Modify: `tests/unit/telegram/test_webhooks.py`
- Modify: `tests/integration/test_health.py`

**Interfaces:**
- `TelegramWebhookBot` adds `set_my_commands(self, commands: list[BotCommand]) -> bool`.
- `configure_telegram_webhooks(...)` registers `start` and `admin` for the main bot before its webhook URL.

- [ ] **Step 1: Write failing command-menu and composition tests**

```python
@pytest.mark.asyncio
async def test_main_bot_registers_owner_commands() -> None:
    access_bot = FakeBot()
    business_bot = FakeBot()

    await configure_telegram_webhooks(settings, access_bot, business_bot)

    assert [(command.command, command.description) for command in business_bot.commands] == [
        ("start", "Открыть панель управления"),
        ("admin", "Открыть панель управления"),
    ]
    assert access_bot.commands == []
```

- [ ] **Step 2: Run focused tests to verify RED**

Run: `python -m pytest -q tests/unit/telegram/test_webhooks.py`

Expected: failure because no commands are registered.

- [ ] **Step 3: Implement startup composition**

Import `BotCommand`, call `business_bot.set_my_commands([...])` in `configure_telegram_webhooks`, and extend the protocol. In `create_app`, instantiate `ListOwnerHandoffChats(tenants, chats)` and `ResumeOwnerChatAI(tenants, chats)` and pass them to `create_business_router`.

- [ ] **Step 4: Run focused composition tests to verify GREEN**

Run: `python -m pytest -q tests/unit/telegram/test_webhooks.py tests/integration/test_health.py`

Expected: all tests pass.

- [ ] **Step 5: Commit the completed task**

```bash
git add src/app/infrastructure/telegram/webhooks.py src/app/main.py tests/unit/telegram/test_webhooks.py tests/integration/test_health.py
git commit -m "feat(owner): register panel commands"
```

### Task 5: Verify the feature branch

**Files:**
- Modify only if verification reveals a defect in the files above.

- [ ] **Step 1: Run all non-database tests**

Run:

```bash
python -m pytest -q tests/unit tests/test_project_layout.py tests/test_container_contract.py tests/integration/test_health.py tests/integration/access/test_access_webhook.py tests/integration/tenants/test_business_webhook.py
```

Expected: all selected tests pass.

- [ ] **Step 2: Run static analysis**

Run: `python -m ruff check .`

Expected: `All checks passed!`.

- [ ] **Step 3: Run full tests when PostgreSQL is reachable**

Run: `python -m pytest -q`

Expected: all tests pass. If `localhost:5432` remains unavailable, record the connection failure separately from code-test results.

- [ ] **Step 4: Inspect the final diff and status**

Run: `git diff main...HEAD --check; git status --short`

Expected: no whitespace errors and no unintended files.

## Plan Self-Review

- Spec coverage: Task 1 covers customer-safe uncertainty handling; Task 2 covers server-authorized chat controls; Task 3 covers panel usability, `/start`/`/admin` resilience and callbacks; Task 4 covers command-menu discovery and composition; Task 5 covers verification.
- Placeholder scan: no `TODO`, `TBD`, or deferred implementation steps are present.
- Type consistency: chat use cases use `TenantPort.get_by_owner`, persistence returns `CustomerChat`, and callback chat identifiers remain `int` from router through use case to repository.
