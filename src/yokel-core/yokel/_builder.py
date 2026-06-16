from __future__ import annotations

import dataclasses
from dataclasses import dataclass

from yokel._conversation import Conversation
from yokel.core.models import Response
from yokel.providers import Provider


@dataclass(frozen=True)
class MessageBuilder:
    """Immutable builder for a single LLM request.

    Every chain method returns a new MessageBuilder; the original is unchanged.
    This makes it safe to branch from a shared base configuration:

        base = y.model("claude-opus-4-8").system("You are helpful.")
        r1 = base.user("Question one").send()
        r2 = base.user("Question two").send()   # base is still unchanged

    Do not construct directly. Obtain via Yokel.model().
    """

    _provider: Provider
    _model: str
    _max_tokens: int
    _system: str | None
    _messages: tuple[dict[str, str], ...]

    def system(self, text: str) -> MessageBuilder:
        """Set or replace the system prompt.

        Args:
            text: The system prompt text. Replaces any previously set prompt.

        Returns:
            A new MessageBuilder with _system set to text.
        """
        return dataclasses.replace(self, _system=text)

    def user(self, text: str) -> MessageBuilder:
        """Append a user turn to the message list.

        Args:
            text: The user message content.

        Returns:
            A new MessageBuilder with the user turn appended to _messages.
        """
        return dataclasses.replace(
            self, _messages=(*self._messages, {"role": "user", "content": text})
        )

    def assistant(self, text: str) -> MessageBuilder:
        """Append an assistant turn for few-shot priming.

        Args:
            text: The assistant message content.

        Returns:
            A new MessageBuilder with the assistant turn appended to _messages.
        """
        return dataclasses.replace(
            self,
            _messages=(*self._messages, {"role": "assistant", "content": text}),
        )

    def max_tokens(self, n: int) -> MessageBuilder:
        """Override the maximum token count for this request.

        Args:
            n: The new upper bound on tokens the provider may generate.

        Returns:
            A new MessageBuilder with _max_tokens set to n.
        """
        return dataclasses.replace(self, _max_tokens=n)

    def send(self) -> Response:
        """Dispatch the current message list to the provider.

        Returns:
            A normalised Response with text, model, stop_reason, and usage.

        Raises:
            ValueError: _messages is empty — no user turn was added before send.
            AuthError: Provider authentication rejected the request.
            ProviderError: Provider returned an upstream HTTP or API error.
        """
        if not self._messages:
            raise ValueError(
                "Cannot send: no messages have been added. "
                "Call .user() at least once before .send()."
            )

        return self._provider.send(
            messages=self._messages,  # type: ignore[arg-type]
            model=self._model,
            system=self._system,
            max_tokens=self._max_tokens,
        )

    def conversation(self) -> Conversation:
        """Create a mutable Conversation capturing this builder's configuration.

        The Conversation inherits model, system, max_tokens, and any messages
        already in this builder as its initial history. Configuration cannot be
        changed after construction.

        Returns:
            A new Conversation ready for multi-turn use.
        """
        return Conversation(
            provider=self._provider,
            model=self._model,
            system=self._system,
            max_tokens=self._max_tokens,
            history=list(self._messages),
        )
