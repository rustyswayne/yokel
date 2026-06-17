---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-006: Structured Error Hierarchy Wrapping Provider Exceptions

## Context

Each provider SDK raises its own exception types (e.g. `anthropic.AuthenticationError`, `anthropic.APIStatusError`). If yokel lets these propagate, callers must import provider SDKs just to handle errors — defeating the provider-agnostic goal. Options considered:

- Let SDK exceptions propagate unwrapped (callers must import SDKs)
- Catch all exceptions and raise a single `YokelError` (loses diagnostic detail)
- Define a small typed hierarchy in `yokel-core` and map SDK exceptions into it

## Decision

We will define a **structured error hierarchy in `yokel.core.errors`** and require every provider to map its operational exceptions into it:

```
YokelError                          # base for all yokel errors
  ├── AuthError                     # bad or missing API key
  ├── ProviderError                 # upstream HTTP or API error
  │     .status_code: int
  │     .provider_message: str
  └── UnknownModelError             # no installed provider claims the model ID
```

Providers catch their SDK's authentication and HTTP errors and re-raise as `AuthError` or `ProviderError`. Non-operational exceptions (SDK contract violations, programmer errors) propagate **unwrapped** — they indicate bugs, not recoverable conditions.

## Consequences

### Positive

- Callers handle auth and upstream errors with `from yokel.core.errors import AuthError, ProviderError` — no provider SDK import needed
- `ProviderError.status_code` allows HTTP-level handling (e.g. rate-limit detection) without SDK knowledge
- `UnknownModelError` gives a clear message when a model ID has no registered provider

### Negative

- Some SDK error detail may not survive translation (e.g. Anthropic's error body structure is reduced to `provider_message: str`)
- Provider authors must write and maintain the mapping; gaps mean SDK exceptions leak

### Neutral

- Non-operational exceptions propagate unwrapped — callers will see SDK exception types in truly unexpected cases
- `AuthError` is raised at provider construction time (fail-early) when auth cannot be resolved

## Notes

- **Convention:** when a provider exception carries no HTTP status at all (e.g. a
  connection-level failure), map it to `ProviderError(status_code=0, ...)`. Established by
  [[2026-06-17-anthropic-provider]] §5 for `anthropic.APIConnectionError`; later providers
  facing the same "no HTTP status" case should reuse `0` rather than inventing a new
  sentinel.
- See `01-api-design.md` → "Error Hierarchy" for the full spec and usage example
- See `03-provider-anthropic.md` → "Error Mapping" for the Anthropic exception map
- `AuthError` raised at construction time (not at `.send()` time) is a deliberate fail-early policy
- [Python built-in exceptions](https://docs.python.org/3/library/exceptions.html) — base `Exception` class and hierarchy conventions
- [Anthropic API errors](https://docs.anthropic.com/en/api/errors) — Anthropic SDK exception types and HTTP status codes that map to `AuthError` / `ProviderError`
