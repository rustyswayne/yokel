---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-002: Fluent Immutable Builder as Public API

## Context

yokel needs a public API that is ergonomic for one-shot requests, safe when branching from a shared base configuration, and free of hidden state bugs. Options considered:

- Mutable builder (each method mutates self and returns self)
- Immutable builder (each method returns a new instance)
- Plain function calls (`yokel.send(model=..., system=..., user=...)`)
- Config-object style (`yokel.Request(model=...).send()`)

## Decision

We will use a **fluent immutable builder** as the sole public chain API. `MessageBuilder` is a **frozen dataclass**; every chain method calls `dataclasses.replace(self, ...)` and returns a new instance. `_messages` is stored as a `tuple` (not a list) so the immutability guarantee is enforced at the data-structure level. `yokel.model(id)` is the single factory that creates the initial builder; there is no `.model()` method on an existing builder.

```python
base = yokel.model("claude-opus-4-8").system("You are helpful.")
r1 = base.user("Question 1").send()   # base unchanged
r2 = base.user("Question 2").send()   # independent request
```

## Consequences

### Positive

- Branching from a shared base is safe — no risk of cross-contaminating independent requests
- Eliminates an entire class of hidden state bugs
- Simple mental model: every chain call produces a value, nothing mutates

### Negative

- More object allocations per chain call compared to a mutable builder
- Callers must use assignment (`r = base.user("msg").send()`) rather than in-place mutation

### Neutral

- Multi-turn conversations require `Conversation`, which is deliberately mutable (see ADR-005)
- The immutability guarantee makes `MessageBuilder` safe to share across threads

## Notes

- See `02-architecture.md` → "Immutability Mechanism" for the frozen dataclass implementation
- See `01-api-design.md` for the full builder method table and branching examples
- [Python `dataclasses` module](https://docs.python.org/3/library/dataclasses.html) — `@dataclass(frozen=True)`, `dataclasses.replace()`
