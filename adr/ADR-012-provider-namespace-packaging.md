---
date: 2026-06-17
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-012: Provider Namespace Packaging — `yokel.<provider>` via PEP 420

## Context

[[2026-06-17-anthropic-provider]] §1 originally proposed a flat top-level import package,
`yokel_anthropic` (underscore), to avoid converting `yokel-core`'s `yokel/` from a regular
package to a PEP 420 namespace package — a restructure that would relocate `yokel-core`'s
public API out of `yokel/__init__.py`. [[ADR-003-plugin-based-provider-resolver]]'s own
example string, however, already used the namespaced form (`"yokel.anthropic,
AnthropicProvider"`), and `Scratch.md` assumed the same. Open Question 1 of the design
(resolved as D3 in its [[_discussions/2026-06-17-anthropic-provider|discussion doc]])
reversed the flat-package proposal in favor of the namespace form, creating the naming
divergence this ADR formally records and resolves.

Options considered:

- Flat top-level package `yokel_anthropic` (avoids the `yokel-core` restructure, but
  diverges from ADR-003's own example and `Scratch.md`'s vision).
- `yokel.anthropic` as a PEP 420 implicit namespace sub-package (matches ADR-003 and
  `Scratch.md`, but requires converting `yokel-core`'s `yokel/` to a namespace package and
  moving its public API out of `yokel/__init__.py`).

## Decision

Provider packages adopt the **`yokel.<provider>` PEP 420 namespace import path**, while
**keeping the PyPI distribution name `yokel_<provider>`** (e.g. `pyproject.toml`
`name = "yokel-anthropic"`, installed via `pip install yokel-anthropic`, imported as
`import yokel.anthropic`). This requires converting `yokel-core`'s `yokel/` package from a
regular package to an implicit namespace package and relocating its public API
(`Yokel`, `MessageBuilder`, `Conversation`, `register_provider`, etc.) out of
`yokel/__init__.py` into a location that survives the namespace-package conversion. That
restructure is in scope for `yokel-anthropic`'s implementation, not deferred to a later
release.

```
src/yokel-anthropic/
└── yokel/
    └── anthropic/
        ├── __init__.py        ← public re-exports + import-time default registration
        └── _provider.py       ← AnthropicProvider
```

## Consequences

### Positive

- Aligns with [[ADR-003-plugin-based-provider-resolver]]'s existing example and
  `Scratch.md`'s intended vision — no further naming divergence for `yokel-openai` /
  `yokel-genai` to resolve later.
- `import yokel.anthropic` reads naturally alongside `import yokel` for consumers.

### Negative

- Requires restructuring `yokel-core`'s `yokel/` package (regular → PEP 420 namespace) and
  relocating its public API out of `yokel/__init__.py` — a breaking change to
  `yokel-core`'s internal layout that must land before or alongside `yokel-anthropic`.
- Every provider package's `pyproject.toml` must declare a namespace-package-compatible
  `packages` entry (no `__init__.py` at the `yokel/` level within that distribution),
  which [[ADR-001-poetry-monorepo]]'s example layout did not anticipate.

### Neutral

- The distribution name (`yokel_anthropic`) and the import path (`yokel.anthropic`) are now
  intentionally different strings — this is expected and not a naming bug.

## Notes

- See [[2026-06-17-anthropic-provider]] §1 ("Package & namespace") and Open Question 1 /
  D3 in [[_discussions/2026-06-17-anthropic-provider]] for the full reversal rationale.
- [[ADR-001-poetry-monorepo]] should be read alongside this ADR for the packaging mechanics
  of namespace sub-packages within the monorepo.
- [PEP 420 — Implicit Namespace Packages](https://peps.python.org/pep-0420/)
