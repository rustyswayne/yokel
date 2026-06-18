from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class Tool:
    """A provider-agnostic tool declaration.

    Attributes:
        name: The tool's name, also its registry key (ADR-013 design,
            Section 2).
        description: A human-readable description shown to the model.
        input_schema: A JSON Schema dict describing the tool's input.
            Unvalidated by yokel; passed to the provider as-is.
    """

    name: str
    description: str
    input_schema: dict[str, Any]

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Tool:
        """Build a Tool from a plain dict (fixtures/persistence symmetry).

        Args:
            d: A dict with "name", "description", and "input_schema" keys.

        Returns:
            A Tool constructed from the dict's values.
        """
        return cls(
            name=d["name"],
            description=d["description"],
            input_schema=d["input_schema"],
        )


@dataclass(frozen=True)
class ToolCall:
    """A normalized tool-use request returned by the model.

    Attributes:
        id: Provider-issued correlation id, echoed back via
            `Conversation.tool_result()`.
        name: The name of the Tool the model wants to invoke.
        input: Arguments for the call, decoded from the provider's JSON.
    """

    id: str
    name: str
    input: dict[str, Any]


@dataclass(frozen=True)
class Response:
    text: str
    model: str
    stop_reason: str
    usage: Usage
    tool_calls: tuple[ToolCall, ...] = ()
    raw_content: Any = None
