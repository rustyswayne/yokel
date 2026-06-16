---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-001: Poetry Monorepo with monoranger-plugin

## Context

yokel consists of a shared core package (`yokel-core`) and multiple provider packages (`yokel-anthropic`, future `yokel-openai`, etc.). These packages must be developed and tested together in a tight feedback loop, yet each must be independently buildable and publishable to PyPI so users install only the providers they need. Options considered:

- Separate git repositories per package (hard to coordinate changes)
- Single flat package (forces users to install all provider SDKs)
- Monorepo with a workspace manager

## Decision

We will use a **Poetry monorepo managed with `poetry-monoranger-plugin`**. The repo root (`src/pyproject.toml`) is `package-mode = false`; its `group.projects` entry installs `yokel-core` and provider packages in editable/develop mode. Each sub-package under `src/` has its own `pyproject.toml`, is independently buildable, and is publishable as a standalone distribution.

## Consequences

### Positive

- Coordinated changes across core and providers land in a single commit/PR
- Each distribution is independently publishable; users install only what they need (`pip install yokel-anthropic`)
- Standard Poetry tooling applies at the sub-package level

### Negative

- Requires the `poetry-monoranger-plugin` (not built into Poetry); contributors must install it
- Root `pyproject.toml` is non-standard (`package-mode = false`) and may confuse newcomers

### Neutral

- All packages share a single git history and CI pipeline
- Sub-package versioning is managed independently; they do not need to be in sync

## Notes

- See `02-architecture.md` → "Monorepo Layout" for the full directory tree
- `poetry-monoranger-plugin` must be listed in `[tool.poetry.requires-plugins]` in the root `pyproject.toml`
- [Poetry documentation](https://python-poetry.org/docs/) — dependency management, `pyproject.toml` reference, workspace concepts
- [Python Packaging User Guide](https://packaging.python.org/en/latest/) — building and publishing distributions to PyPI
