---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-003: Plugin-Based Lazy-Import Provider Resolver

## Context

`yokel-core` must operate without any provider SDK installed. Provider packages must be able to register themselves so that `yokel.model(id)` resolves correctly without modifying `yokel-core`. Options considered:

- Hardcode provider classes inside `yokel-core` (creates SDK dependencies in core)
- Python `importlib.metadata` entry points (requires packaging ceremony; entry points only load at install time)
- Runtime registration via a pattern registry + `importlib` lazy import (no packaging ceremony, lazy loading)

## Decision

Provider packages register **model ID patterns** with the resolver at import time using the `PluginConfigurationSection`: a mapping of `{"pattern": "module, class"}` strings (e.g. `"claude-*"` → `"yokel.anthropic, AnthropicProvider"`). When `yokel.model(id)` is called, the resolver iterates registered patterns, finds the first match, then uses `importlib.import_module` + `getattr` to dynamically import and instantiate the provider. If no pattern matches, `UnknownModelError` is raised with the unmatched model ID.

Registration itself happens through one of two paths, settled in [[2026-06-17-anthropic-provider]] §6 and [[ADR-011-yokel-singleton-and-default-provider-registry]]:

```python
# (a) ergonomic path — writes into the process-level default registry;
#     Yokel seeds its plugins section from this at construction
yokel.register_provider("claude-*", "yokel.anthropic, AnthropicProvider", default=True)

# (b) explicit path — writes directly into a given manager's plugins section,
#     no global state touched (test isolation)
register(target, manager_or_yokel)
```

## Consequences

### Positive

- `yokel-core` has zero provider SDK dependencies; it is importable in any environment
- Adding a new provider requires no changes to `yokel-core`
- No `importlib.metadata` entry point ceremony; registration is a single call in the provider package's `__init__.py`
- SDK import is deferred until `yokel.model(id)` is first called for a matching ID

### Negative

- Registration errors (bad module/class string) only surface at call time, not at install time
- Pattern matching is first-registered-wins; conflicting registrations (two packages claiming `"claude-*"`) silently resolve to whichever registered first

### Neutral

- Each provider SDK is imported lazily on first use, not at `import yokel` time
- The `PluginConfigurationSection` validates the `"module, class"` shape on write, catching typos at registration time

## Notes

- See `05-core.md` → "Plugin System & Provider Resolver" for the full implementation spec
- See `02-architecture.md` → "Provider Resolution" for the call flow
- `UnknownModelError` is part of the error hierarchy; see ADR-006
- [Python `importlib` module](https://docs.python.org/3/library/importlib.html) — `import_module`, `getattr`-based dynamic class loading
- [Python `importlib.metadata`](https://docs.python.org/3/library/importlib.metadata.html) — the entry-point mechanism considered and rejected
