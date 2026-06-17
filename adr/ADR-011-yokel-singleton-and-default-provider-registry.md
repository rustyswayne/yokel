---
date: 2026-06-17
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-011: Yokel Singleton Lifecycle & Process-Level Default Provider Registry

## Context

[[2026-06-17-anthropic-provider]] (§6, Open Questions 2, D1/D2/D7 in its
[[_discussions/2026-06-17-anthropic-provider|discussion doc]]) needs `import yokel_anthropic`
to make a subsequently constructed `Yokel()` resolve `claude-*` without any explicit wiring
call — the import-and-go ergonomic the [[2026-06-16-yokel-class]] design advertises.
[[ADR-007-explicit-configuration-no-global-state]] decided there is **no module-level
global config object** and that each `ConfigurationManager` is independently constructed
and injectable. Two design decisions on `yokel-anthropic` sit at the edge of that boundary:

- **`Yokel` is confirmed to be a singleton** — not a fresh independent instance per
  `Yokel()` call, as ADR-007's original framing assumed.
- A **process-level default provider registry** is needed so provider packages can deposit
  `{pattern: "module, class"}` entries that any `Yokel` can see at construction, without
  importing the provider package being a `ConfigurationManager`-mutation call site.

Options considered:

- Leave ADR-007 as strictly worded and require every caller to explicitly wire provider
  registration (breaks the advertised `import yokel_anthropic; Yokel().model(...)` usage).
- Make `ConfigurationManager` itself a singleton (defeats ADR-007's testability goal —
  cross-test state leakage returns).
- Keep `ConfigurationManager` injectable and testable, but admit two narrow, explicit
  exceptions: the `Yokel` singleton itself, and an append-only registry of provider
  *discovery metadata* (not mutable application configuration).

## Decision

We amend the no-global-state boundary set by [[ADR-007-explicit-configuration-no-global-state]]
with two narrow, explicit exceptions:

1. **`Yokel` is a process-level singleton.** There is one `Yokel`, not one per `Yokel()`
   call. Test isolation that previously relied on constructing independent `Yokel()`
   instances must instead use `Yokel(config=...)` injection (see [[2026-06-17-anthropic-provider]]
   §"Open Questions" #2 / D7) or the explicit per-instance `register(target)` path (§6b)
   to avoid cross-test leakage.
2. **A process-level default provider registry** — an append-only mapping of
   `{pattern: "module, class"}` — is admitted as a sanctioned global. It is exposed through
   a single public entry point, `yokel.register_provider(pattern, target, *, default: bool
   = True)`. `Yokel`'s `ConfigurationManager` seeds its `plugins` section from this registry
   for entries registered with `default=True`. The registry holds **pattern strings only** —
   no API keys, secrets, or other mutable application state ever pass through it (PATs are
   resolved per-provider-instance at construction time, never at registration; see
   [[2026-06-17-anthropic-provider]] §2, D1).

Everything else in ADR-007 stands: there is still no global mutable *application*
configuration object, and `Yokel(config=...)` + explicit `register(target)` remain available
to bypass both the singleton's default config and the default registry entirely for test
isolation.

## Consequences

### Positive

- `import yokel_anthropic; Yokel().model("claude-opus-4-8")` works with zero explicit
  wiring, preserving the ergonomic the [[2026-06-16-yokel-class]] design promised.
- The registry is append-only, pattern-only metadata — it cannot leak secrets and cannot be
  used to mutate already-resolved application state.
- Explicit, injectable construction (`Yokel(config=...)`, `register(target)`) still exists
  for tests that need full isolation from the singleton's default state.

### Negative

- `Yokel` being a singleton is a real reversal of the independent-instance framing in
  [[ADR-007-explicit-configuration-no-global-state]] and [[2026-06-16-yokel-class]]; both
  documents' "each `Yokel()` owns an independent `ConfigurationManager`" language is now
  stale and should be read in light of this ADR.
- Tests that relied on bare `Yokel()` construction for isolation must switch to
  `Yokel(config=...)` or explicit `register(...)` — a behavior change for any code written
  against the original ADR-007 framing.

### Neutral

- The default registry's "first-registered-wins" pattern-matching behavior from
  [[ADR-003-plugin-based-provider-resolver]] is unchanged by this decision.

## Notes

- See [[2026-06-17-anthropic-provider]] §6 for the full registration design and
  [[_discussions/2026-06-17-anthropic-provider]] D1, D2, D7 for the resolved discussion.
- [[ADR-007-explicit-configuration-no-global-state]] remains Accepted; this ADR narrows its
  "no global state" boundary rather than superseding it.
