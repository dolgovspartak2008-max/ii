# AI Intent Routing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Route greetings, unrelated questions, and profile-uncertain business questions to distinct customer-safe responses.

**Architecture:** Add two provider markers for out-of-scope and owner-escalation outcomes. The application use case maps them to constants; the OpenRouter adapter prompt defines the model behavior.

**Tech Stack:** Python 3.12, OpenRouter-compatible HTTP API, pytest.

## Global Constraints

- Do not infer business facts absent from the saved profile.
- Preserve the `ИИ:` prefix for ordinary model replies.
- A clearly unrelated message never receives an owner-escalation response.

---

### Task 1: Map new provider markers in the application service

**Files:**
- Modify: `src/app/application/ai/use_cases.py`
- Modify: `tests/unit/ai/test_use_cases.py`

- [ ] **Step 1: Write failing tests**

```python
assert await service.execute(tenant_id, 100, "вопрос") == OWNER_WAIT_TEXT
```

Use `[[NEEDS_OWNER]]` and `[[OUT_OF_SCOPE]]` fake responses, including one
formatted variant of each. Also test standalone greetings such as
`Здравствуйте` and `Привет!` return a fixed greeting without calling the
responder.

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest tests/unit/ai/test_use_cases.py -q`

Expected: failure because only `[[NEEDS_REPHRASE]]` is currently recognized.

- [ ] **Step 3: Implement marker normalization and fixed responses**

Keep the old marker as an alias for out-of-scope compatibility, add
`NEEDS_OWNER_TOKEN`, return `OWNER_WAIT_TEXT` only for that marker, and
recognize standalone greetings before the responder call.

- [ ] **Step 4: Run focused tests**

Run: `python -m pytest tests/unit/ai/test_use_cases.py -q`

Expected: all AI use-case tests pass.

### Task 2: Define the model policy

**Files:**
- Modify: `src/app/infrastructure/ai/openrouter.py`
- Modify: `tests/unit/ai/test_openrouter.py`

- [ ] **Step 1: Write a failing prompt-content assertion**

Assert that the outbound system prompt says greetings receive a natural reply,
out-of-scope requests return `[[OUT_OF_SCOPE]]`, and relevant-but-unknown
requests return `[[NEEDS_OWNER]]`.

- [ ] **Step 2: Run the focused test**

Run: `python -m pytest tests/unit/ai/test_openrouter.py -q`

Expected: failure because the current prompt maps all non-answers to one marker.

- [ ] **Step 3: Update the system prompt**

Use the exact decision rules from the design and prohibit unsupported facts.

- [ ] **Step 4: Verify**

Run: `python -m pytest -q && python -m ruff check .`

Expected: all tests pass and Ruff reports no violations.
