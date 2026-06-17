---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-007: Explicit Injectable ConfigurationManager — No Global Mutable State

## Context

Configuration (provider auth, plugin registrations) must be accessible across the system without creating hidden coupling. The common shortcut — a module-level singleton (`yokel.config`) — introduces global mutable state, makes tests fragile (state leaks between test cases), and makes yokel harder to embed in larger applications with their own config systems. Options considered:

- Module-level config singleton (common but problematic)
- Config passed explicitly as a parameter to every call site (too verbose)
- An injectable `ConfigurationManager` owned by the resolver, passed down where needed

## Decision

We will use an **explicit, injectable `ConfigurationManager`** in `yokel-core`. There is no module-level global config object. The manager owns named sections; two sections always exist: **`plugins`** (a `PluginConfigurationSection` storing `"module, class"` strings for provider registration) and **`value_store`** (a plain section for key/value config like `anthropic.api_key`). Configuration changes emit `configuration_changing` / `configuration_changed` events via `EventHandler`, decoupling state changes from reactions.

## Consequences

### Positive

- Fully testable — tests can construct an isolated `ConfigurationManager` with no cross-test state leakage
- Applications embedding yokel can supply their own config without fighting a global singleton
- The event system (`on_configuration_changed`) lets code react to config changes without polling

### Negative

- Slightly more boilerplate than a module-level singleton when wiring the manager in
- Callers who need to override config must obtain a reference to the manager rather than importing a global

### Neutral

- `ConfigurationManager` is constructed once by the resolver; callers using `yokel.model(id)` never interact with it directly in normal usage
- Loading from `~/.yokel.yaml` (via `pyyaml`, already a dependency of `yokel-core`) is deferred to post-MVP; the machinery exists today

## Notes

- **Amended by [[ADR-011-yokel-singleton-and-default-provider-registry]]:** `Yokel` is a
  process-level singleton and a narrow, pattern-only default provider registry is admitted
  as a sanctioned global. The "no global mutable state" decision here still holds for
  application configuration; see ADR-011 for the exact boundary.
- See `05-core.md` → "Configuration System" for the full section/manager/event spec
- `pyyaml` is listed as a `yokel-core` dependency even in v0.1 to avoid a breaking change when file loading ships
- [Python `abc` module](https://docs.python.org/3/library/abc.html) — `ABC`, `abstractmethod` used for `IConfigurationManager` and related interfaces
- [PyYAML documentation](https://pyyaml.org/wiki/PyYAMLDocumentation) — `yaml.safe_load` / `yaml.dump` used for config file loading and display
