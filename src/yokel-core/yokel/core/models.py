from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


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
class ToolChoice:
    """A normalized request-level policy for whether/which tool the model must use.

    Attributes:
        mode: One of "auto" (model decides, the default), "required" (must
            call some tool), "none" (tools declared but unusable), or "tool"
            (must call the tool named by `name`).
        name: The tool to force when `mode == "tool"`. Must be `None` for
            every other mode.
    """

    mode: Literal["auto", "required", "none", "tool"]
    name: str | None = None

    def __post_init__(self) -> None:
        if self.mode == "tool" and not self.name:
            raise ValueError("ToolChoice mode 'tool' requires a non-empty name.")

        if self.mode != "tool" and self.name is not None:
            raise ValueError(f"ToolChoice mode '{self.mode}' must not set name.")

    @classmethod
    def auto(cls) -> ToolChoice:
        """The model decides freely whether to call a tool."""
        return cls(mode="auto")

    @classmethod
    def required(cls) -> ToolChoice:
        """The model must call at least one of the declared tools."""
        return cls(mode="required")

    @classmethod
    def none(cls) -> ToolChoice:
        """Tools may be declared but the model may not call any of them."""
        return cls(mode="none")

    @classmethod
    def tool(cls, name: str) -> ToolChoice:
        """The model must call the tool named `name`.

        Args:
            name: The tool to force.
        """
        return cls(mode="tool", name=name)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ToolChoice:
        """Build a ToolChoice from a plain dict (fixtures/persistence symmetry).

        Args:
            d: A dict with a "mode" key and an optional "name" key.

        Returns:
            A ToolChoice constructed from the dict's values.
        """
        return cls(mode=d["mode"], name=d.get("name"))

    def validate_against(self, tools: tuple[Tool, ...]) -> None:
        """Fail fast if this choice cannot be honoured by the resolved tools.

        Args:
            tools: The tools resolved for the request this choice applies to.

        Raises:
            ValueError: mode is "required" or "tool" but `tools` is empty, or
                mode is "tool" but `name` does not match any tool in `tools`.
        """
        if self.mode in ("auto", "none"):
            return

        if not tools:
            raise ValueError(
                f"tool_choice mode '{self.mode}' requires at least one tool, "
                "but no tools were resolved for this request."
            )

        if self.mode == "tool" and not any(tool.name == self.name for tool in tools):
            raise ValueError(
                f"tool_choice names tool '{self.name}', which is not in the "
                "resolved tool set for this request."
            )


@dataclass(frozen=True)
class Response:
    text: str
    model: str
    stop_reason: str
    usage: Usage
    tool_calls: tuple[ToolCall, ...] = ()
    raw_content: Any = None
