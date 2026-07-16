# Russian Response Quality Design

## Problem

The provider prompt does not require grammatical Russian, correct spacing, or a
direct answer. The model can therefore return malformed stock phrases.

## Decision

Use one strict, explicit response-quality policy in the system prompt and lower
sampling variability to 0.2. The model must internally proofread grammar,
agreement, spelling, word spacing, and punctuation before replying. It answers
only the customer's direct question, does not repeat the business description
without need, and never invents facts or prices.

A second corrective model pass is intentionally omitted: it increases latency
and could accidentally alter factual details such as prices.

## Verification

The OpenRouter unit test captures the request payload and asserts the quality
policy and low temperature are present.

# Russian Response Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require grammatically correct Russian replies with proper word spacing and focused wording.

**Architecture:** The OpenRouter adapter owns both the generation settings and the system-level writing policy. No post-processing rewrites business facts.

**Tech Stack:** Python 3.12, httpx, pytest.

## Global Constraints

- Preserve prices and other business facts exactly as supplied.
- Never generate an unrequested catalogue summary.
- Keep the existing marker protocol unchanged.

### Task 1: Add the failing request-payload assertion

**Files:**
- Modify: `tests/unit/ai/test_openrouter.py`

- [ ] Assert `payload["temperature"] == 0.2` and that the system prompt requires grammatical Russian, correct word spacing, punctuation, and a direct answer.
- [ ] Run: `python -m pytest tests/unit/ai/test_openrouter.py -q`
- [ ] Confirm the test fails because the current adapter lacks these settings.

### Task 2: Implement and verify the policy

**Files:**
- Modify: `src/app/infrastructure/ai/openrouter.py`

- [ ] Add `"temperature": 0.2` to the outbound completion payload.
- [ ] Add the exact Russian quality rules to the system prompt.
- [ ] Run: `python -m pytest -q && python -m ruff check .`
- [ ] Confirm all tests and static checks pass.

