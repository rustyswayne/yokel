# yokel

A focused Python library that provides a **unified, provider-agnostic API** for LLM providers. Call any supported LLM through one consistent interface; swap providers by changing a single string.

## What it is

yokel abstracts the differences between LLM provider SDKs so that application code stays clean and portable. Its job is to normalize request building and response shapes across providers — nothing more.

Explicitly **out of scope**: agent orchestration, prompt templating, response caching, retry/backoff logic, logging, and rate limiting. Those concerns belong in your application layer.

## Features

- **Fluent immutable builder** — chain methods to construct requests; every step returns a new instance so shared base configurations are safe to branch from.
- **Unified response model** — `response.text`, `response.model`, `response.stop_reason`, and `response.usage` mean the same thing regardless of provider.
- **Multi-turn conversations** — `Conversation` accumulates message history automatically; no manual list management.
- **Plugin-based provider resolver** — provider packages register themselves at import time; no changes to `yokel-core` are ever required.
- **Structured error hierarchy** — `AuthError`, `ProviderError`, and `UnknownModelError` let you handle failures without importing any provider SDK.
- **No global state** — an injectable `ConfigurationManager` keeps configuration isolated and fully testable.

## Quick start

```python
import yokel

# One-shot request
response = yokel.model("claude-opus-4-8").system("You are helpful.").user("Hello!").send()
print(response.text)

# Branch from a shared base — neither call affects the other
base = yokel.model("claude-opus-4-8").system("You are a Python expert.")
r1 = base.user("Explain list comprehensions.").send()
r2 = base.user("Explain generators.").send()
```

## Multi-turn conversations

```python
conv = yokel.model("claude-opus-4-8").conversation()
r1 = conv.user("Hello!").send()
r2 = conv.user("What did I just say?").send()  # full history sent automatically
```

## Error handling

```python
from yokel.core.errors import AuthError, ProviderError, UnknownModelError

try:
    response = yokel.model("claude-opus-4-8").user("Hello!").send()
except AuthError:
    print("Bad or missing API key")
except ProviderError as e:
    print(f"Provider returned HTTP {e.status_code}: {e.provider_message}")
except UnknownModelError:
    print("No installed provider claims that model ID")
```

## Provider packages

Install only the providers you need:

```bash
pip install yokel-anthropic   # Anthropic / Claude support
```

Each provider package registers its model ID patterns with the resolver at import time. Once a provider is imported, `yokel.model(id)` resolves it automatically.

## Repository structure

This is a **Poetry monorepo** managed with [`poetry-monoranger-plugin`](https://github.com/devbyte1328/poetry-monoranger-plugin). Each sub-package under `src/` is independently buildable and publishable.

```
yokel/
├── adr/                  # Architecture Decision Records
├── src/
│   ├── pyproject.toml    # Workspace root (package-mode = false)
│   └── yokel-core/       # Core library: configuration, events, interfaces, errors
└── requirements.txt
```

## Development setup

**Requirements:** Python 3.12+, [Poetry](https://python-poetry.org/) with `poetry-monoranger-plugin`.

```bash
# Install Poetry plugin (one-time)
pipx install poetry
pipx inject poetry poetry-monoranger-plugin

# Install all workspace dependencies
cd src
poetry install

# Install quality tools
poetry run pip install "ruff>=0.4.0" mypy types-pyyaml
```

## Running checks

All commands run from the `src/` directory inside the Poetry virtual environment.

```bash
# Lint
poetry run ruff check --select E,W,F,I,CLB .

# Format check
poetry run ruff format --check .

# Type check (strict)
poetry run mypy --strict .

# Tests (unit only, no live API key required)
poetry run pytest -m "not requires_api_key"
```

Tests that require a live provider API key are marked `@pytest.mark.requires_api_key` and are excluded from the default CI run.

## Architecture decisions

The `adr/` directory contains Architecture Decision Records that document the key design choices:

| ADR | Decision |
|-----|----------|
| [ADR-001](adr/ADR-001-poetry-monorepo.md) | Poetry monorepo with `poetry-monoranger-plugin` |
| [ADR-002](adr/ADR-002-fluent-immutable-builder.md) | Fluent immutable builder as public API |
| [ADR-003](adr/ADR-003-plugin-based-provider-resolver.md) | Plugin-based lazy-import provider resolver |
| [ADR-004](adr/ADR-004-unified-response-model.md) | Unified frozen dataclass response model |
| [ADR-005](adr/ADR-005-mutable-conversation-object.md) | Mutable `Conversation` as the sole stateful object |
| [ADR-006](adr/ADR-006-error-hierarchy.md) | Structured error hierarchy wrapping provider exceptions |
| [ADR-007](adr/ADR-007-explicit-configuration-no-global-state.md) | Explicit injectable `ConfigurationManager` — no global state |
| [ADR-008](adr/ADR-008-focused-scope-provider-abstraction-only.md) | Focused scope — provider abstraction only |
| [ADR-009](adr/ADR-009-code-quality-tooling.md) | Code quality tooling (Ruff, mypy, pytest) |

## License

See [LICENSE](LICENSE) for details.
