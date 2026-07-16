# Owner Panel Reliability and Conversation Controls Design

## Purpose

Make the main Telegram Business bot reliable and comfortable for the configured
platform owner and every approved owner. Both `/start` and `/admin` open the
same owner panel. The panel makes
the business profile, AI status and handed-off customer chats visible and
actionable. A customer must never see the provider's internal uncertainty
marker.

## Scope

- Register `/start` and `/admin` in the main bot's Telegram command menu.
- Deliver each new access application to the configured administrator through
  the main bot, with approve and reject controls handled by that same bot.
- Route both commands through one panel-opening helper which clears abandoned
  profile-edit state and reports owner-facing errors instead of failing
  silently.
- Keep the existing profile editor, with explicit cancel and a return to the
  refreshed panel after every successful save.
- Replace the flat panel with a concise dashboard: business profile, AI
  switch, handed-off dialogs and help.
- Let an owner list their handed-off dialogs and resume AI for a selected
  dialog. Every operation resolves the tenant from the callback sender and
  verifies the selected chat belongs to that tenant.
- Normalize the OpenRouter `[[NEEDS_REPHRASE]]` marker before customer delivery.
  The exact marker, including an optional `ИИ:` prefix or Markdown code
  formatting, maps to the fixed Russian rephrasing request. Other replies
  retain the existing `ИИ:` prefix behavior.

## Command and Panel Flow

`/start` and `/admin` first authorize the sender and idempotently create the
sender's tenant. The Telegram ID configured as `ADMIN_TELEGRAM_ID` is the
platform owner and is authorized directly, without first submitting an access
application. Every other sender must have an approved access application.
Both commands clear an unfinished FSM edit and render the same current
dashboard. This lets the operator manage the primary bot immediately, while
preserving the application review flow for all other tenants.

## Application Review Flow

The access bot remains the public intake surface: a visitor opens it and
submits an access application. The notifier sends the new application to
`ADMIN_TELEGRAM_ID` through the main bot, not the intake bot. The main bot
registers the typed approve/reject callback handler and uses the existing
application use cases, which already enforce that only `ADMIN_TELEGRAM_ID` may
review. The result notification is still sent through the access bot so the
applicant receives it in the conversation they have already opened.

The dashboard contains these actions:

1. **Мой бизнес** — current name and description, or a clear empty-profile
   message.
2. **Изменить профиль** — the existing name, description and confirmation
   wizard; Cancel clears state and returns to the dashboard.
3. **ИИ: включён/выключен** — immediately changes the tenant-wide switch and
   refreshes the dashboard.
4. **Диалоги у вас** — lists only `human_handoff` chats for the sender's tenant
   and provides a `Передать ИИ` action for each. Resuming switches the selected
   chat back to `active` and refreshes the list.
5. **Помощь** — concise explanation of how handoff, resume and the AI switch
   work.

No callback contains a tenant identifier. A callback may carry only a Telegram
chat id; the server resolves the owner tenant and performs the state change with
both `tenant_id` and `telegram_chat_id`.

## Reliability Rules

- The command menu is registered at application startup together with
  webhooks, using the main bot only.
- Dashboard commands and callbacks catch missing tenant/profile state and
  return a recoverable Russian message. Callback queries are acknowledged in
  every handled branch.
- A stale profile-edit state never prevents `/start` or `/admin` from opening
  the panel.
- The panel uses the latest dashboard state after every mutation; it never
  trusts a displayed status or a callback payload as authorization.

## AI Uncertainty Handling

The provider prompt continues to require the exact `[[NEEDS_REPHRASE]]`
marker when business context is insufficient, the question is unrelated, or
the request is unclear. Before prefixing an answer, the application removes
optional leading `ИИ:` and code-formatting from a candidate marker. If the
normalized result is exactly the marker, it returns:

> Извините, я не понял вопрос. Пожалуйста, переформулируйте его или уточните детали.

Provider errors, an empty reply, a disabled tenant, missing business profile,
or a handed-off chat still produce no automated customer message.

## Persistence and Application Boundaries

`PostgresBusinessChatRepository` gains tenant-scoped methods to list
`human_handoff` chats and resume one such chat. Application use cases resolve
the owner to a tenant before calling those methods. The Telegram adapter only
uses the application use cases; it does not query a tenant from callback data.

No new database table or migration is required: `customer_chats.state` already
stores both `active` and `human_handoff` states.

## Tests and Acceptance Criteria

- `/start` and `/admin` each invoke the same panel path; the configured
  platform owner opens it without an access application, while an unapproved
  non-owner receives the access instruction. `/admin` clears stale FSM state.
- Dispatcher-level tests feed actual command and callback updates through the
  business router, proving that Telegram routes both commands and each panel
  callback to a handler rather than merely rendering button metadata.
- A new-application notification uses the main bot, its review callback is
  handled by the main dispatcher, and applicant result notifications use the
  access bot.
- The command menu exposes both commands for the main bot.
- Owner callbacks cannot list or resume another tenant's chat.
- A handed-off chat becomes active only through the authenticated owner's
  resume action.
- Exact, prefixed and code-formatted uncertainty markers map to the fixed
  customer-safe text; ordinary replies retain one `ИИ:` prefix.
- Focused unit tests and Ruff pass. Database integration tests are run when
  PostgreSQL is reachable.

## Self-Review

- No tenant ID is trusted from Telegram input.
- The design reuses existing chat state and does not introduce unrelated RAG,
  billing or knowledge-base work.
- Error handling and state-reset behavior are explicit, and every proposed
  user action has a defined result.
