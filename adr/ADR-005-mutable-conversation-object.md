---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-005: Mutable Conversation as the Sole Stateful Object

## Context

Multi-turn conversations require accumulating message history across multiple `.send()` calls. The immutable builder (ADR-002) cannot accumulate history — each call produces a new instance. Options considered:

- Extend the immutable builder to accumulate history (breaks immutability guarantee)
- Return a new builder with updated history from each `.send()` (caller must thread state manually)
- Introduce a separate mutable object solely for multi-turn sessions

## Decision

We will introduce **`Conversation`** as a **deliberately mutable** wrapper around a snapshot of the builder's configuration. `Conversation` is the only mutable object in the request path. It is created via `builder.conversation()`, which captures the builder's model, system, and max_tokens at construction time — these cannot be changed mid-conversation. Each `.user(text)` call appends to a mutable `list[dict]`; each `.send()` appends the assistant turn after receiving the response.

```python
conv = yokel.model("claude-opus-4-8").conversation()
r1 = conv.user("Hello!").send()
r2 = conv.user("What did I just say?").send()   # history included automatically
```

## Consequences

### Positive

- Multi-turn history accumulates automatically — callers don't manage message lists
- Clear separation: immutable `MessageBuilder` for independent requests; mutable `Conversation` for sessions
- `Conversation` cannot be branched (intentional); each session is a single linear thread

### Negative

- `conv.user(...).send()` looks like the builder chain but mutates in place — this asymmetry can surprise callers
- `Conversation` is not thread-safe; concurrent `.send()` calls on the same instance would corrupt history

### Neutral

- `Conversation` holds a provider reference and a copy of the builder's config — it is not a thin wrapper
- Configuration snapshotted at `builder.conversation()` time; model/system/max_tokens are fixed for the session's lifetime

## Notes

- See `02-architecture.md` → "Conversation" for the implementation spec
- See `01-api-design.md` → "Multi-Turn via .conversation()" for usage examples
- [Python `dataclasses` module](https://docs.python.org/3/library/dataclasses.html) — `@dataclass(frozen=True)` used by the `MessageBuilder` this wraps
