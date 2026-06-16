---
date: 2026-06-16
status: Accepted
deciders: Yokel core team
tags:
  - adr
---

# ADR-004: Unified Frozen Dataclass Response Model

## Context

With multiple providers, application code that reads a response must either branch on the provider (fragile) or receive a normalized type (stable). Options considered:

- Return provider-native response objects (callers must know which SDK they used)
- Return a dict with documented keys (no type safety)
- Define shared frozen dataclasses in `yokel-core` that every provider must produce

## Decision

We will define **`Response` and `Usage` as frozen dataclasses in `yokel-core`**. Every provider implementation is responsible for translating its SDK response into these types before returning. `Response.text`, `Response.model`, `Response.stop_reason`, and `Response.usage` mean the same thing regardless of which provider produced them. `Response` is a value object — frozen, not a handle. Accessing `.text` when no text block is present raises `ValueError`.

```python
@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int

@dataclass(frozen=True)
class Response:
    text: str
    model: str
    stop_reason: str
    usage: Usage
```

**Serialization:** `yokel-core` does not take a Pydantic dependency. Provider SDKs (e.g. `anthropic`) already bring Pydantic transitively, but `yokel-core` stays dep-free. To close the deserialization gap for test fixtures and conversation persistence, both types expose `from_dict()` classmethods alongside `dataclasses.asdict()` for the outbound direction:

```python
@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int

    @classmethod
    def from_dict(cls, d: dict) -> "Usage":
        return cls(input_tokens=d["input_tokens"], output_tokens=d["output_tokens"])

@dataclass(frozen=True)
class Response:
    text: str
    model: str
    stop_reason: str
    usage: Usage

    @classmethod
    def from_dict(cls, d: dict) -> "Response":
        return cls(
            text=d["text"],
            model=d["model"],
            stop_reason=d["stop_reason"],
            usage=Usage.from_dict(d["usage"]),
        )
```

## Consequences

### Positive

- Application code is fully provider-agnostic — `response.text` works the same whether Anthropic, OpenAI, or any future provider answered
- `frozen=True` makes `Response` safe to cache, store, or pass across threads
- Type-checked at the call site; no dict key errors

### Negative

- Provider-specific fields (e.g. Anthropic's `cache_creation_input_tokens`) are not accessible via `Response`; callers needing them must use the provider SDK directly
- Providers must write and maintain translation code
- `from_dict()` must be updated manually if new fields are added (no automatic schema sync)

### Neutral

- `stop_reason` is a string, not an enum, to avoid having to enumerate every provider's stop reasons in `yokel-core`
- `Usage` covers only `input_tokens` and `output_tokens`; cost calculation is left to the application layer

## Notes

- See `01-api-design.md` → "Response Object" for the full spec
- See `03-provider-anthropic.md` → "Response Mapping" for the Anthropic translation
- [Python `dataclasses` module](https://docs.python.org/3/library/dataclasses.html) — `@dataclass(frozen=True)`, `dataclasses.asdict()`
