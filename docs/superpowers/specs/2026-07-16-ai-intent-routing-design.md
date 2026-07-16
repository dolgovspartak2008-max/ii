# AI Intent Routing Design

## Purpose

Prevent the business assistant from treating greetings and potentially relevant
questions as incomprehensible.

## Decision Rules

- A standalone greeting receives a fixed short greeting and an invitation to
  ask about the business without calling the provider. A longer conversational
  opening is handled by the provider as an ordinary reply.
- A question clearly unrelated to the business returns the existing request to
  rephrase or ask about the business.
- A question that may concern the business but cannot be answered from the
  available profile returns a message that the client should wait for the owner
  or consultant.

## Architecture

The application service recognizes standalone Russian greetings before calling
the provider. The OpenRouter system prompt classifies only the two non-answer states with
separate exact markers: `[[OUT_OF_SCOPE]]` and `[[NEEDS_OWNER]]`. Ordinary
answers, including greetings, remain ordinary text. `GenerateBusinessReply`
normalizes either marker despite an optional `ИИ:` prefix or Markdown code
formatting and maps it to fixed customer-safe Russian text. No tenant data is
trusted from the model response.

## Tests

Unit tests cover standalone greetings plus exact and formatted markers for both
states, while the adapter test asserts that the system prompt distinguishes
greetings, out-of-scope requests, and owner escalation.
