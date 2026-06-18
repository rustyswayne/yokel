---
date: 2026-06-18
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-013: Tool Handler Interface and Core-Executed Tool Loop

## Context

[[2026-06-17-tool-use-support]] (v0.2.0) gives applications the wire-level primitives for
tool use — `Tool`, `ToolCall`, `Response.tool_calls`, `Conversation.tool_result()` — but
deliberately stops short of running anything: the application owns the
`while resp.stop_reason == "tool_use": ...` loop and the dispatch from `ToolCall.name` to
its implementation. [[ADR-008-focused-scope-provider-abstraction-only]] backs this with an
explicit exclusion: "Agent loops and tool orchestration" stay out of yokel.

During v0.2.0 planning, a question surfaced that revisits that exclusion directly: should
yokel itself execute the tool-call loop, given a registry of handler implementations, rather
than leaving every application to write the same `while` loop and dispatch table? Options
considered:

- Keep the boundary exactly as ADR-008 draws it — no change, loop stays entirely
  application-side (status quo).
- Add a thin opt-in loop helper directly to `yokel-core` (e.g.
  `conversation.run_tools(handlers)`) that takes a `dict[str, Callable]` and loops until
  `stop_reason != "tool_use"`.
- Ship the loop helper as a separate, optional package (e.g. `yokel-toolloop`) depending on
  `yokel-core`, so the base library's minimalism is untouched and orchestration lives in an
  explicitly separate artifact.
- Introduce a **`ToolHandlerInterface` interface** in `yokel-core`, let handler implementations be
  authored/registered at the provider level and assigned to a specific `Conversation`, and
  have `yokel-core` itself execute the loop against the registered handlers — using the
  existing `EventHandler` (`yokel/core/events.py`) to emit lifecycle events as the loop runs.

## Decision

We will take the fourth option: **`yokel-core` defines a `ToolHandlerInterface` interface, owns a
tool-loop executor that runs registered handlers, and emits loop-lifecycle events through
the existing `EventHandler`.**

This is a deliberate, scoped reversal of part of ADR-008's "Agent loops and tool
orchestration" exclusion — recorded here rather than silently overridden. The exclusion
still stands for *general* agent orchestration (planning, multi-step task decomposition,
retries across turns); what's now in scope is narrower: executing the handler that
corresponds to a single declared `Tool` when the model requests it, and looping the
send → dispatch → result cycle until the model stops asking for tools. ADR-008 is amended
(see its Notes) to record this carve-out and point here.

Three pieces, to be detailed in a forthcoming design doc:

1. **`ToolHandlerInterface` interface** — a small `metaclass=abc.ABCMeta` type in `yokel-core` that a callable tool
   implementation conforms to (taking a `ToolCall` and returning the result content yokel
   passes to `Conversation.tool_result()`/`MessageBuilder.tool_result()`). Mirrors the shape
   of `ProviderInterface` itself (ADR-008's `__subclasshook__` pattern is a candidate precedent).
2. **Provider-level authoring, conversation-level assignment.** Handler *implementations*
   can be defined alongside a provider package (so a provider can ship handlers that make
   sense for its tool ecosystem), but a handler is *assigned* to a specific `Conversation`
   — the same registry-vs-instance split `Conversation` already uses for `model`/`system`
   (ADR-005). A handler registered on one conversation does not leak into another.
3. **Core-executed loop.** `yokel-core` runs the loop: send → inspect `tool_calls` → look up
   each call's `ToolHandlerInterface` by `Tool.name` → invoke it → submit the result → re-send —
   until `stop_reason != "tool_use"`. The loop emits events via the existing `EventHandler`
   (e.g. a `tool_call_started`/`tool_call_resolved`/`loop_complete` shape, exact names TBD in
   the design doc) so applications can observe progress. **No event subscriptions ship by
   default** — the emission points exist as a hook for later use (logging, UI progress,
   metrics), not as a feature with built-in consumers yet.

What this decision does **not** do: it does not turn yokel into a general agent framework.
There is still no planning, no multi-tool-call strategy beyond "run what the model asked
for," and no cross-provider orchestration concerns beyond the tool-call dispatch loop
itself. An application that wants LangGraph-style orchestration on top of yokel still can —
this executor is a convenience for the common case, not a replacement for it.

## Consequences

### Positive

- Removes the most common piece of boilerplate every yokel application would otherwise
  write by hand (the `while stop_reason == "tool_use"` loop and a name→handler dispatch
  table) — a real ergonomics win for the "understand tool use" goal driving this phase.
- Reuses existing core machinery (`EventHandler`) rather than inventing a second observation
  mechanism.
- Keeping handler *assignment* at the `Conversation` level (not global) preserves the
  per-session isolation `Conversation` already guarantees (ADR-005) — no cross-conversation
  handler leakage.

### Negative

- This is a genuine, if scoped, reversal of ADR-008's orchestration exclusion — the
  boundary "yokel does not run loops" is no longer absolute, and future scope-creep
  pressure ("can the loop also retry on tool error?", "can it run handlers in parallel?")
  now has a foothold to push from. The design doc following this ADR must keep the loop's
  surface deliberately small.
- `yokel-core` grows a new abstraction (`ToolHandlerInterface`) and a new stateful executor
  alongside `Conversation`, increasing the bar for understanding the library's core.
- Provider-authored handlers blur the "providers own translation, core owns orchestration"
  separation slightly — a handler living in a provider package but executed by core means
  provider packages now ship code that participates in core's loop, not just request/response
  translation.

### Neutral

- The `EventHandler` emission points are added with no default subscribers — applications
  must opt in to observe the loop; nothing changes for code that ignores events entirely.
- This ADR settles *that* the loop lives in core and *what shape* the decision takes; the
  concrete API (method names, `ToolHandlerInterface` signature, error handling when a handler raises
  or no handler matches a `ToolCall.name`) is deferred to the implementing design doc.

## Notes

- See [[2026-06-17-tool-use-support]] for the wire-level primitives this loop is built on.
- See [[ADR-008-focused-scope-provider-abstraction-only]] for the general orchestration
  exclusion this ADR carves a scoped exception into.
- See [[ADR-005-mutable-conversation-object]] for the per-`Conversation` isolation pattern
  this decision follows for handler assignment.
- A design doc detailing `ToolHandlerInterface`'s exact shape, the executor's API, and error handling
  is the immediate next step before any implementation.
