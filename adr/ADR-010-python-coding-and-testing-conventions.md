---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-010: Python Coding and Testing Conventions

## Context

[[ADR-009-code-quality-tooling|ADR-009]] established the toolchain (Ruff, mypy, pytest). That ADR left unspecified the structural and stylistic conventions that govern how code is organised and how tests are written. Without explicit decisions in these areas, contributors will diverge: class layouts become inconsistent, test files proliferate in different shapes, public APIs ship without docstrings, and type-checking fails because new packages are missing PEP 561 markers.

This ADR captures the conventions that complete the quality story ADR-009 started.

## Decision

### Code Organisation

**Class member order — mandatory for all classes:**

1. Constants and class-level variables
2. `__init__`
3. Public properties (getters/setters)
4. Protected properties (`_property`)
5. Private properties (`__property`)
6. Static public methods (`@staticmethod`, no underscore)
7. Public methods (no underscore prefix)
8. Static protected methods
9. Protected methods (`_method`)
10. Static private methods
11. Private methods (`__method`) — always last

**Access level conventions:**

| Prefix | Level | External interface? | Type hints required? | Docstring required? |
|---|---|---|---|---|
| none | Public | Yes | Yes | Yes |
| `_` | Protected | No (module/package internal) | Yes | No |
| `__` | Private | No (class internal) | Yes | No |

**Maximum nesting depth: 1 level.** Use guard clauses (early returns) to eliminate inner nesting. Extract deeper blocks into private helper methods named to reveal intent.

**No bare `except:`.** Always name the exception type. If suppression is intentional, add a comment; CLB rules flag empty handlers that lack one.

**Inline suppression is last resort.** `# noqa:` and `# type: ignore` must include the rule code and a comment explaining the justification. Treat any such line as a code-review flag.

### Naming Conventions

**Amendment (2026-06-18):** Base-class naming depends on *how* the class declares itself
abstract, not just that it's meant to be subclassed:

| Declaration style | Naming | Example |
|---|---|---|
| `class Foo(metaclass=abc.ABCMeta):` — pure contract, no inherited state or implementation | Suffix `Interface` | `ProviderInterface` |
| `class Foo(abc.ABC):` — abstract base that carries shared state, helper methods, or partial implementation alongside the abstract bits | Prefix `Abstract` | `AbstractFoo` |

`ProviderInterface` is declared with `metaclass=abc.ABCMeta` directly (no inherited
implementation, just the `send()` contract and a `__subclasshook__`), so it takes the
`Interface` suffix. A future base class that instead subclasses `abc.ABC` to share concrete
behavior across implementations would take the `Abstract` prefix instead, not the
`Interface` suffix — the two are not interchangeable spellings of the same thing.

**`typing.Protocol` is not used for this purpose.** Pure contracts are declared with
`metaclass=abc.ABCMeta`, full stop — not `Protocol`. This keeps one mechanism for
"interface" across the codebase (explicit `abc` registration/subclassing, checkable with a
plain `isinstance()`) rather than two competing ones with different runtime semantics.

Concrete implementations are never prefixed or suffixed for this reason: `AnthropicProvider`
implements `ProviderInterface`; a `FakeProvider` test double also implements
`ProviderInterface`. This disambiguates "the contract" from "a thing that satisfies the
contract" at the call site (`isinstance(x, ProviderInterface)` reads as a contract check;
`AnthropicProvider` reads as a concrete adapter).

This does not apply to exception classes (`ProviderError` stays as-is — it is not an
interface) or to feature/concept names used in prose or ADR titles (e.g. "provider
abstraction," "Provider Namespace Packaging") — only to the actual interface/abstract-base
type identifier.

### Documentation

**Public functions require Google-style docstrings** with Args, Returns, and Raises sections where applicable:

```python
def create_response(text: str, model: str, stop_reason: str) -> Response:
    """Build a normalised Response from raw provider output.

    Args:
        text: The generated text returned by the provider.
        model: The model identifier string (e.g. ``"claude-sonnet-4-6"``).
        stop_reason: The reason the provider stopped generating.

    Returns:
        A frozen Response instance.

    Raises:
        ValueError: If stop_reason is not a recognised value.
    """
```

Private and protected functions get at most a single comment line where intent is not obvious from the name. No multi-line docstrings on non-public callables.

### Type Annotations and PEP 561

All functions — public and private — must have fully annotated parameters and return types. `from __future__ import annotations` is the first line of every `.py` file.

**Every new top-level package must ship a PEP 561 marker** so Pylance and mypy can locate its types:

1. Create an empty file at `src/<package_name>/py.typed`.
2. Declare it in `pyproject.toml`:
   ```toml
   [tool.setuptools.package-data]
   <package_name> = ["py.typed"]
   ```

Without this marker, every consumer of the package sees `module is installed, but missing library stubs or py.typed marker`.

For third-party dependencies lacking annotations, create a sibling `<package_name>-stubs` distribution containing `.pyi` files that mirror the public API. Prefer this over per-file `# type: ignore` suppression when a dependency is used in multiple places.

### Configuration

Environment variables are accessed only from each app's config module — never via `os.environ` in business logic. Per-app configuration lives in `<app>.config`.

### Testing

**Class-based organisation — mandatory for all new test files:**

```python
"""Tests for <module_name>: <comma-separated list of functions tested>."""

from __future__ import annotations

# 1. Standard library
# 2. Third-party
# 3. Project (always absolute imports)
# 4. Fake/stub classes (before fixtures and tests)
# 5. Test classes

class TestFunctionName:
    """Tests for function_name."""

    def test_<function>_<scenario>_<expected>(self) -> None: ...
```

Existing flat-function test files do not require migration.

**Test naming convention:** `test_<function>_<scenario>_<expected>`

```
test_create_response_with_end_turn_returns_complete
test_create_response_with_empty_text_raises_value_error
test_resolve_provider_with_unknown_name_raises
```

**Arrange-Act-Assert — section comments are mandatory:**

```python
def test_response_is_complete_for_end_turn(self) -> None:
    """Response.is_complete returns True when stop_reason is end_turn."""
    # Arrange
    response = Response(text="hi", model="m", stop_reason="end_turn", usage=Usage(0, 0))

    # Act
    result = response.is_complete

    # Assert
    assert result is True, "Expected is_complete=True for stop_reason='end_turn'"
```

**Every `assert` must include a failure message** as the second argument. The message must be human-readable and contain enough context to diagnose without re-running.

**`@pytest.mark.parametrize` must include `ids=[...]`** for readability in the test report:

```python
@pytest.mark.parametrize(
    "stop_reason,expected",
    [
        ("end_turn", True),
        ("max_tokens", False),
        ("", False),
    ],
    ids=["end-turn", "max-tokens", "empty"],
)
def test_response_is_complete(self, stop_reason: str, expected: bool) -> None: ...
```

**Mocking:**

- Mock at the boundary (external APIs, provider SDKs); test real objects everywhere else.
- Use `MagicMock(spec=RealType)` where the real type is stable — the spec catches wrong attribute access.
- Configure mock return values in the test body (Arrange section), not in shared fixtures, when they vary across tests.
- Tests that require a live external service must be marked with the appropriate marker (`@pytest.mark.requires_api_key`, `@pytest.mark.requires_databricks`, etc.) and are excluded from the default CI run.

**Pre-test analysis — mandatory before writing any test:**

1. Read the complete source file for the function under test.
2. Verify the exact parameter names, types, defaults, and return shape.
3. Identify which external clients the function calls; plan mocks for each.

**Test discovery — when adding a new test suite:**

- Add the test directory to `python.testing.pytestArgs` in `.vscode/settings.json`.
- Add both `src/` and `tests/` paths to `python.analysis.extraPaths` so Pylance resolves imports.
- Verify discovery with `pytest --collect-only <new-tests-dir>` before committing.
- Do **not** add `__init__.py` to `tests/` directories — multiple `tests/__init__.py` files across packages collide in pytest's rootdir-based import mode.

**Never invoke tests against a system or Conda Python.** Always use `.venv\Scripts\python -m pytest` (Windows) or `.venv/bin/python -m pytest` (POSIX), or the VS Code Test Explorer configured to use the root `.venv`.

## Consequences

### Positive

- Mandatory class member ordering removes a whole category of review nit and makes navigation predictable across all source files.
- Google-style docstrings on public functions surface Args/Returns/Raises in IDE tooltips and any generated documentation.
- PEP 561 markers eliminate the "missing library stubs" noise from mypy and Pylance on every in-repo package.
- Class-based test organisation and the `test_<function>_<scenario>_<expected>` naming convention make it easy to find tests for a given function and to read failures in the test report.
- Mandatory `# Arrange / # Act / # Assert` comments and assertion messages reduce the time to diagnose a failing test from seconds to milliseconds.
- Parametrize IDs make the test report self-explanatory without having to decode index numbers.

### Negative

- Mandatory docstrings on every public function add writing overhead for simple one-liner helpers that happen to be public.
- Class member ordering requires discipline to maintain as classes grow; no automated tool enforces the full ordering (only access-level prefixes are inferable).
- `MagicMock(spec=...)` can fail on dynamic attributes; contributors must know when to drop back to unspec'd mocks.
- Prohibiting `__init__.py` in test directories is counter-intuitive and will surprise developers coming from projects that use it.

### Neutral

- Class-based test organisation is a new file layout; existing flat-function files are grandfathered and migrate opportunistically.
- PEP 561 stub packages add a small distribution-level artefact for each third-party dependency that lacks annotations; this is standard practice but unfamiliar to some contributors.
- `.vscode/settings.json` must be updated for each new test suite; this is a lightweight but easy-to-forget step.

## Notes

- Companion to [[ADR-009-code-quality-tooling|ADR-009]] — toolchain decisions live there; structural and stylistic conventions live here.
- Detailed patterns, full examples, and the pre-commit checklist are maintained in `.yokel-design/+/python-quality/references/coding.md` and `testing.md`.
- `from __future__ import annotations` as first line of every `.py` file is also specified in ADR-009; repeated here for completeness of the coding standards reference.
