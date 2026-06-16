---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-008: Focused Scope — Provider Abstraction Only

## Context

LLM client libraries frequently grow to include agent orchestration (tool loops, planning), prompt templating, response caching, retry/backoff logic, logging, and rate limiting. Each addition increases complexity, surface area, and maintenance burden, and makes the library harder to compose with specialized tools that do those jobs better. Options considered:

- Expand yokel to cover orchestration, retries, templating, etc.
- Keep yokel strictly focused on provider abstraction

## Decision

**yokel abstracts provider access only.** The library's job is to present a consistent API across installed LLM providers and normalize their responses. Explicitly out of scope:

- Agent loops and tool orchestration
- Prompt templating
- Response caching
- Retry / backoff logic
- Logging
- Rate limiting

These concerns belong in the application layer or in specialized libraries. The internal machinery in `yokel-core` (events, configuration, plugin resolver) exists solely to keep providers swappable cleanly; it is not exposed as a general-purpose framework.

## Consequences

### Positive

- Small, focused, easy to reason about
- Composable — applications can layer retries, caching, and orchestration on top using whichever tools they choose
- Fewer breaking changes as the library evolves
- Stays out of the way of agent frameworks (LangGraph, etc.) that have opinions about tool loops

### Negative

- Callers must implement or source retry logic, caching, and logging themselves
- yokel will not replace heavier LLM frameworks for teams that want batteries included

### Neutral

- The event system and configuration manager are internal; their existence does not make yokel an "application framework"
- Future scope expansions (streaming, tool use, batch API) remain within provider abstraction — they add API surface without adding orchestration concerns

## Notes

- See `00-vision.md` → "What yokel Is Not" for the explicit exclusions
- See `04-mvp-scope.md` → "Explicitly Deferred" for features excluded from v0.1 for this reason
- [LangGraph](https://langchain-ai.github.io/langgraph/) — example of an agent orchestration framework deliberately kept out of scope
