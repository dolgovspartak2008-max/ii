# Owner Panel Direct Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the configured Telegram owner open and operate the business-bot panel through `/start` and `/admin` without a prior access application.

**Architecture:** The authorization decision stays in the owner-onboarding use case. It accepts the configured owner ID directly and retains approved-application authorization for all other Telegram users. The router continues to scope all panel work to the message or callback sender; tests feed real updates into aiogram's dispatcher.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, pytest.

## Global Constraints

- `ADMIN_TELEGRAM_ID` is the only direct owner ID.
- Other users retain the approved-access-application requirement.
- Test the command and callback route through aiogram, not merely button markup.
- Use test-first red-green development.

---

### Task 1: Add direct-owner authorization

**Files:**
- Modify: `src/app/application/tenants/use_cases.py`
- Test: `tests/unit/tenants/test_use_cases.py`

**Interfaces:**
- Consumes: `AccessApprovalPort.get_by_telegram_id()` and `TenantPort.create_for_owner()`.
- Produces: `OnboardApprovedOwner(approvals, tenants, direct_owner_telegram_id)`.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.asyncio
async def test_configured_owner_can_onboard_without_application() -> None:
    tenants = FakeTenants()
    onboarding = OnboardApprovedOwner(
        FakeAccessApprovals(None), tenants, direct_owner_telegram_id=42
    )

    await onboarding.execute(42)

    assert tenants.created_for == [42]
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/unit/tenants/test_use_cases.py::test_configured_owner_can_onboard_without_application -q`

Expected: failure because the current use case requires an approved application for every user.

- [ ] **Step 3: Implement the smallest change**

```python
if owner_telegram_id != self._direct_owner_telegram_id:
    application = await self._approvals.get_by_telegram_id(owner_telegram_id)
    if application is None or application.status is not ApplicationStatus.APPROVED:
        raise OwnerNotApproved("Owner must have an approved access application.")
return await self._tenants.create_for_owner(owner_telegram_id)
```

- [ ] **Step 4: Run all tenant use-case tests**

Run: `python -m pytest tests/unit/tenants/test_use_cases.py -q`

Expected: all tests pass.

### Task 2: Wire configuration and prove routing

**Files:**
- Modify: `src/app/main.py`
- Modify: `tests/unit/tenants/test_business_router.py`

**Interfaces:**
- Consumes: `Settings.admin_telegram_id` and the Task 1 constructor.
- Produces: a business router where the configured owner can open the panel by both commands and invoke a panel callback.

- [ ] **Step 1: Write failing tests for `/start`, `/admin`, and a `show` callback**

The test harness must call `Dispatcher.feed_raw_update()` with updates belonging to Telegram user 42 and assert that the bot sends `Панель управления`, executes the profile action, and acknowledges the callback.

- [ ] **Step 2: Run the focused router tests**

Run: `python -m pytest tests/unit/tenants/test_business_router.py -q`

Expected: the direct-owner command test fails until the configured ID is injected.

- [ ] **Step 3: Pass `settings.admin_telegram_id` to onboarding**

```python
OnboardApprovedOwner(repository, tenants, settings.admin_telegram_id)
```

Keep all callback authorization based on `callback.from_user.id`.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/unit/tenants/test_business_router.py tests/integration/test_health.py -q`

Expected: commands, callback routing, and application construction pass.

### Task 3: Verify and document

**Files:**
- Modify: `docs/superpowers/specs/2026-07-16-owner-panel-reliability-design.md`
- Create: `docs/superpowers/plans/2026-07-16-owner-panel-direct-access.md`

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -q`

Expected: all tests pass.

- [ ] **Step 2: Run static analysis**

Run: `python -m ruff check .`

Expected: `All checks passed!`.

- [ ] **Step 3: Review the scope**

Run: `git diff --check && git diff --stat main...HEAD`

Expected: no whitespace errors; changes are limited to onboarding, dependency injection, routing tests, and documentation.

### Task 4: Move application review to the main bot

**Files:**
- Modify: `src/app/infrastructure/telegram/access_bot/notifier.py`
- Modify: `src/app/infrastructure/telegram/access_bot/router.py`
- Modify: `src/app/main.py`
- Create: `tests/unit/access/test_notifier.py`
- Modify: `tests/unit/tenants/test_business_router.py`

**Interfaces:**
- Consumes: existing `SubmitAccessApplication`, `ApproveAccessApplication`,
  `RejectAccessApplication`, and `AccessReviewCallback`.
- Produces: `AiogramAccessNotifier(applicant_bot, review_bot, admin_telegram_id)`;
  a submission-only access router; and an access-review router included in the
  main bot dispatcher.

- [ ] **Step 1: Write failing notifier and dispatcher tests**

Assert that `notify_admin()` sends through a fake main bot, `notify_applicant()`
sends through a fake access bot, and a review callback fed to the main
dispatcher acknowledges the callback and invokes approval.

- [ ] **Step 2: Run focused tests**

Run: `python -m pytest tests/unit/access tests/unit/tenants/test_business_router.py -q`

Expected: failure because the notifier has one bot and review callbacks are
registered in the access router.

- [ ] **Step 3: Implement the split routing**

Keep `create_access_router(submit)` for `/start` and `access:submit`; add
`create_access_review_router(approve, reject)` for `AccessReviewCallback`.
Construct the notifier with both bots and include the review router in
`business_dispatcher` before business events.

- [ ] **Step 4: Verify focused and full suites**

Run: `python -m pytest -q && python -m ruff check .`

Expected: all tests pass and Ruff reports no violations.
