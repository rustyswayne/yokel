---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-009: Code Quality Tooling

## Context

yokel is a library intended to be read and contributed to over time. We need a consistent, enforced set of tools for formatting, linting, and type checking across both `yokel-core` and all provider packages. Key requirements:

- Zero-tolerance CI (no warnings-as-suggestions; the build either passes or it doesn't)
- Catch type errors before runtime
- Enforce clean code structure (no bare `except`, no broad exception blocks)
- Fast enough to run on every save in an IDE and in CI without friction

Options considered for linting/formatting: Ruff alone, Ruff + flake8, Black + isort + flake8.
Options considered for type checking: mypy, Pyright (standalone CLI), Pylance (VS Code extension, Pyright-backed).

## Decision

We will use the following tool chain across all packages:

**Ruff** — formatting and the primary lint layer. Enabled rule sets:
- `E`, `W` — pycodestyle errors and warnings
- `F` — Pyflakes
- `I` — isort (import ordering)
- `CLB` — `flake8-clean-block` rules. Specific subrules enforced:
  - `CLB001` — empty code block (`except`, `finally`, `else`) with only `pass`; must either remove the block or add a comment explaining why it is safe to suppress
  - `CLB002` — unnecessary nested block; flatten with `and` or extract a helper
  - `CLB003` — unused exception handler; either handle the exception or remove the clause

**mypy** — static type checking in CI, run in strict mode (`--strict`). mypy is the authoritative type-check gate; a mypy failure blocks merge.

**Pylance** — IDE type checking (VS Code). Pylance runs Pyright under the hood and gives inline feedback during development. It is not part of CI — it is a developer ergonomics tool. Pylance settings (e.g. `"python.analysis.typeCheckingMode": "strict"`) are committed to `.vscode/settings.json` so all contributors get consistent IDE behaviour.

**pytest** — test discovery and execution. Configuration lives in `pyproject.toml` under `[tool.pytest.ini_options]`:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
```
Tests that require a live API key are marked `@pytest.mark.requires_api_key` and are excluded from the default CI run; they are opt-in for integration testing.

**Type annotations** — all public and internal code must be fully type-annotated using the `typing` module (or built-in generics where available). `from __future__ import annotations` is the first line of every `.py` file to enable postponed evaluation of annotations and forward references without string quoting.

Pre-push checklist (enforced in CI):
```powershell
ruff check .          # zero errors
ruff format --check . # zero violations
mypy .                # zero errors (strict)
pytest -m "not requires_api_key"  # all unit tests pass
```

### Testing Standards

**Structure — AAA:** Every test follows Arrange / Act / Assert with a blank line between sections. Each test validates one behaviour.

**Assertion messages:** All assertions include a failure message with enough context to diagnose without re-running:
```python
assert result == expected, f"Expected {expected!r}, got {result!r} for input {input_data!r}"
```

**Parametrize for variations:** Use `@pytest.mark.parametrize` instead of copy-paste tests. Always include edge cases (empty input, `None`, boundary values):
```python
@pytest.mark.parametrize("stop_reason,expected", [
    ("end_turn", True),
    ("max_tokens", False),
    ("", False),
])
def test_response_is_complete(stop_reason: str, expected: bool) -> None:
    r = Response(text="hi", model="m", stop_reason=stop_reason, usage=Usage(0, 0))
    assert r.is_complete == expected, f"stop_reason={stop_reason!r}"
```

**Coverage target:** ≥ 80% line coverage. Run with `pytest --cov`. Cover both the happy path and error cases — don't only test success scenarios.

**Mocking policy:** Mock at the boundary (external APIs, provider SDKs); test real objects everywhere else. Verify both return values and side effects when mocking.

### Coding Patterns

**Early returns / guard clauses:** Return early to keep nesting shallow. Maximum 1 level of nesting inside a function body; extract helpers when logic requires deeper nesting.

**No bare `except:`** — always name the exception type. If suppression is intentional, add a comment; the CLB rules will flag empty handlers that lack one.

**Inline ignores are last resort:** `# noqa:` and `# type: ignore` must include the rule code and a comment explaining why the suppression is justified. Treat any such line as a code-review flag.

## Consequences

### Positive

- Ruff replaces Black + isort + flake8 for the fast feedback loop; single tool, single config block in `pyproject.toml`
- `CLB` rules eliminate an entire class of silent exception-swallowing bugs at lint time
- mypy strict mode catches missing annotations and type errors before runtime
- Pylance gives developers immediate inline feedback without waiting for CI
- `from __future__ import annotations` enables forward references cleanly and future-proofs annotation syntax
- `@pytest.mark.parametrize` enforces systematic edge-case coverage without copy-paste test code
- Separating `requires_api_key` tests via a marker keeps the default CI run fast and offline-capable

### Negative

- mypy strict mode has a steeper onboarding curve; third-party stubs (`types-pyyaml`, etc.) must be installed alongside dev dependencies
- `CLB` rules may require refactoring existing exception handling patterns that are idiomatic but technically broad
- Pylance and mypy can disagree on edge cases (Pylance uses Pyright's type engine; mypy uses its own); mypy is the authoritative CI gate
- Mandatory assertion messages and coverage targets require discipline in code review; tools do not enforce them automatically

### Neutral

- `from __future__ import annotations` is a required first line in every `.py` file — enforced by convention and code review, not by a lint rule
- Tool configuration lives in `pyproject.toml` (`[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`); no separate `.flake8`, `mypy.ini`, or `pytest.ini`

## Notes

- Root `CLAUDE.md` pre-push checklist reflects these tools
- mypy stubs needed at minimum: `types-pyyaml` (for `yokel-core`)
- Ruff's `CLB` support requires `ruff >= 0.4.0` and the `flake8-clean-block` plugin enabled via `[tool.ruff.lint] select`
- Dev dependencies belong under `[project.optional-dependencies] dev` in each sub-package's `pyproject.toml`; install with `pip install -e ".[dev]"`
- Coverage is measured with `pytest --cov`; the 80% floor is a guideline reviewed in PRs, not a hard CI gate (for now)
- [Ruff documentation](https://docs.astral.sh/ruff/) — rule reference, configuration, `pyproject.toml` integration
- [mypy documentation](https://mypy.readthedocs.io/) — strict mode flags, stub packages, configuration reference
- [Pyright documentation](https://microsoft.github.io/pyright/) — the type engine underlying Pylance; useful for diagnosing mypy/Pylance disagreements
- [Pylance (VS Code extension)](https://marketplace.visualstudio.com/items?itemName=ms-python.vscode-pylance) — IDE install and settings reference
- [pytest documentation](https://docs.pytest.org/) — fixtures, markers, parametrize, coverage plugin
- [PEP 563 — Postponed Evaluation of Annotations](https://peps.python.org/pep-0563/) — the spec behind `from __future__ import annotations`
