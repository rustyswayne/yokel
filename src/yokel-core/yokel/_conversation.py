from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from yokel.core.errors import UnknownToolError
from yokel.providers import ProviderInterface

if TYPE_CHECKING:
    from yokel.core.models import Response, Tool, ToolChoice


class Conversation:
    """Mutable multi-turn conversation session.

    Obtain via MessageBuilder.conversation(). The model, system prompt, and
    max_tokens are frozen at construction time. Message history accumulates
    with each .user()/.send() cycle.

    Not thread-safe. Concurrent .send() calls on the same instance corrupt history.

    Example:
        conv = y.model("claude-opus-4-8").system("You are helpful.").conversation()
        r1 = conv.user("Hello").send()
        r2 = conv.user("What did I just say?").send()
    """

    def __init__(
        self,
        provider: ProviderInterface,
        model: str,
        system: str | None,
        max_tokens: int,
        history: list[dict[str, Any]] | None = None,
        tool_names: tuple[str, ...] = (),
        tool_resolver: Callable[[str], Tool | None] | None = None,
        tool_choice: ToolChoice | None = None,
    ) -> None:
        self.__provider = provider
        self.__model = model
        self.__system = system
        self.__max_tokens = max_tokens
        self.__history: list[dict[str, Any]] = (
            list(history) if history is not None else []
        )
        self.__tool_names = tool_names
        self.__tool_resolver = tool_resolver
        self.__tool_choice = tool_choice

    @property
    def model(self) -> str:
        """The model identifier this conversation targets."""
        return self.__model

    @property
    def system(self) -> str | None:
        """The system prompt, or None if none was set."""
        return self.__system

    @property
    def max_tokens(self) -> int:
        """The maximum token count for each send call."""
        return self.__max_tokens

    @property
    def history(self) -> list[dict[str, Any]]:
        """A shallow copy of the current message history."""
        return list(self.__history)

    def user(self, text: str) -> Conversation:
        """Append a user turn and return self for chaining.

        Note: Unlike MessageBuilder chain methods, this mutates the Conversation
        in place. The returned value is the same object.

        Args:
            text: The user message content.

        Returns:
            This Conversation instance (mutated in place).
        """
        self.__history.append({"role": "user", "content": text, "kind": "text"})
        return self

    def tool_choice(self, choice: ToolChoice) -> Conversation:
        """Set or replace the tool_choice policy and return self for chaining.

        Sticky: applies to every subsequent .send() call on this Conversation,
        like model/system, until replaced by another call to this method.

        Args:
            choice: The normalized tool_choice to apply.

        Returns:
            This Conversation instance (mutated in place).
        """
        self.__tool_choice = choice
        return self

    def tool_result(
        self, tool_use_id: str, content: str, *, is_error: bool = False
    ) -> Conversation:
        """Append a tool-result block for tool_use_id and return self for chaining.

        Multiple calls before the next .send() accumulate into a single user
        turn (Anthropic requires all results for one assistant turn batched
        together), rather than producing separate turns.

        Args:
            tool_use_id: The ToolCall.id this result answers.
            content: The tool's result, as a string.
            is_error: Whether the tool execution failed.

        Returns:
            This Conversation instance (mutated in place).
        """
        block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }
        if self.__history and self.__history[-1].get("kind") == "tool_result":
            self.__history[-1]["content"].append(block)
        else:
            self.__history.append(
                {"role": "user", "content": [block], "kind": "tool_result"}
            )

        return self

    def send(self) -> Response:
        """Resolve tools and send the accumulated conversation to the provider.

        Appends the assistant response to history automatically, including on
        truncated responses (stop_reason == 'max_tokens'). The appended turn
        is the provider's re-encoded replay of (text, tool_calls), tagged
        kind="tool_use" when the response requested tool calls, else "text".

        Returns:
            A normalised Response containing text, model, stop_reason, usage,
            and any requested tool calls.

        Raises:
            ValueError: History is empty, the last message is not a user
                turn (a tool_result turn counts as a user turn), or the
                tool_choice cannot be honoured by the resolved tools.
            UnknownToolError: A name in this Conversation's tool_names does
                not resolve against the tool registry.
            AuthError: Provider rejected authentication.
            ProviderError: Provider returned an upstream error.
        """
        if not self.__history:
            raise ValueError(
                "Cannot send: conversation history is empty. "
                "Call .user() before .send()."
            )

        if self.__history[-1]["role"] != "user":
            raise ValueError(
                "Cannot send: the last message is not a user turn. "
                "Call .user() or .tool_result() before calling .send() again."
            )

        resolved_tools = self.__resolve_tools()
        if self.__tool_choice is not None:
            self.__tool_choice.validate_against(resolved_tools)

        response = self.__provider.send(
            messages=tuple(self.__history),
            model=self.__model,
            system=self.__system,
            max_tokens=self.__max_tokens,
            tools=resolved_tools,
            tool_choice=self.__tool_choice,
        )
        encoded = self.__provider.encode_assistant_turn(response)
        kind = "tool_use" if response.tool_calls else "text"
        self.__history.append(
            {"role": "assistant", "content": encoded["content"], "kind": kind}
        )
        return response

    def _reset(self) -> None:
        """Clear all message history. Intended for testing."""
        self.__history.clear()

    def __resolve_tools(self) -> tuple[Tool, ...]:
        """Resolve tool_names against tool_resolver, in order.

        Raises:
            UnknownToolError: A name does not resolve against the registry.
        """
        resolved: list[Tool] = []
        for name in self.__tool_names:
            tool = self.__tool_resolver(name) if self.__tool_resolver else None
            if tool is None:
                raise UnknownToolError(name)

            resolved.append(tool)

        return tuple(resolved)
