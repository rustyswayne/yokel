from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from yokel.providers import ProviderInterface

if TYPE_CHECKING:
    from yokel.core.models import Response, Tool


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
        history: list[dict[str, str]] | None = None,
        tool_names: tuple[str, ...] = (),
        tool_resolver: Callable[[str], Tool | None] | None = None,
    ) -> None:
        self.__provider = provider
        self.__model = model
        self.__system = system
        self.__max_tokens = max_tokens
        self.__history: list[dict[str, str]] = (
            list(history) if history is not None else []
        )
        self.__tool_names = tool_names
        self.__tool_resolver = tool_resolver

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
    def history(self) -> list[dict[str, str]]:
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
        self.__history.append({"role": "user", "content": text})
        return self

    def send(self) -> Response:
        """Send the accumulated conversation to the provider.

        Appends the assistant response to history automatically, including on
        truncated responses (stop_reason == 'max_tokens').

        Returns:
            A normalised Response containing text, model, stop_reason, and usage.

        Raises:
            ValueError: History is empty or the last message is not a user turn.
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
                "Call .user() before calling .send() again."
            )

        response = self.__provider.send(
            messages=tuple(self.__history),
            model=self.__model,
            system=self.__system,
            max_tokens=self.__max_tokens,
        )
        self.__history.append({"role": "assistant", "content": response.text})
        return response

    def _reset(self) -> None:
        """Clear all message history. Intended for testing."""
        self.__history.clear()
