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

## Amendment (2026-06-18): Tool use is the first realized future-scope expansion

[[2026-06-17-tool-use-support]] (v0.2.0) is the first of the "future scope expansions" named above to actually land, and it confirms the line drawn in this ADR: tool use is split into a **wire-level half** (declaring tools, receiving tool-call requests, submitting tool results — provider abstraction) and a **loop half** (deciding which tool to run, executing it, re-prompting until the model stops — orchestration). yokel implements only the former.

Concretely, in scope under this ADR: `Tool`/`ToolCall` value objects, the `tools` parameter on `ProviderInterface.send()`, and `ProviderInterface.encode_assistant_turn()` for replaying a tool-use turn into history. Still explicitly out of scope: an executor that calls application functions, and any `while stop_reason == "tool_use"` loop baked into `yokel-core` — both remain the application's responsibility, per the "Agent loops and tool orchestration" exclusion above.

This confirms the boundary is workable in practice, not just in principle: tool use expands `ProviderInterface`'s contract (`tools` parameter, `encode_assistant_turn` method) without adding any orchestration concern to `yokel-core` itself.

## Amendment (2026-06-18): Scoped carve-out for a core-executed tool-call loop

[[ADR-013-tool-handler-interface-and-core-loop-executor]] reverses part of the "Agent loops and tool orchestration" exclusion above: `yokel-core` will define a `ToolHandlerInterface` interface and execute the send → dispatch → result loop for declared tools, emitting progress via the existing `EventHandler`. The exclusion is **not** lifted in general — there is still no planning, no multi-step task decomposition, and no cross-provider orchestration in yokel. The carve-out is narrow: running the handler that corresponds to a single declared `Tool` when the model asks for it, and looping that cycle until the model stops asking. See ADR-013 for the full decision and its negative consequences (this is treated as a real boundary erosion to watch, not a free reversal).

## Notes

- See `00-vision.md` → "What yokel Is Not" for the explicit exclusions
- See `04-mvp-scope.md` → "Explicitly Deferred" for features excluded from v0.1 for this reason
- [LangGraph](https://langchain-ai.github.io/langgraph/) — example of an agent orchestration framework deliberately kept out of scope
