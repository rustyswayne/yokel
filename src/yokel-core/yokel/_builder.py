from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Any, Callable

from yokel._conversation import Conversation
from yokel.core.errors import UnknownToolError
from yokel.core.models import Response, Tool
from yokel.providers import ProviderInterface


@dataclass(frozen=True)
class MessageBuilder:
    """Immutable builder for a single LLM request.

    Every chain method that builds up a request returns a new MessageBuilder;
    the original is unchanged. This makes it safe to branch from a shared base
    configuration:

        base = y.model("claude-opus-4-8").system("You are helpful.")
        r1 = base.user("Question one").send()
        r2 = base.user("Question two").send()   # base is still unchanged

    Do not construct directly. Obtain via Yokel.model().
    """

    _provider: ProviderInterface
    _model: str
    _max_tokens: int
    _system: str | None
    _messages: tuple[dict[str, Any], ...]
    _tool_resolver: Callable[[str], Tool | None]
    _tool_names: tuple[str, ...] = ()
    _last_response: Response | None = field(default=None, compare=False)
    _tool_result_used: bool = field(default=False, compare=False)

    def system(self, text: str) -> MessageBuilder:
        """Set or replace the system prompt.

        Args:
            text: The system prompt text. Replaces any previously set prompt.

        Returns:
            A new MessageBuilder with _system set to text.
        """
        return self.__replace(_system=text)

    def user(self, text: str) -> MessageBuilder:
        """Append a user turn to the message list.

        Args:
            text: The user message content.

        Returns:
            A new MessageBuilder with the user turn appended to _messages.
        """
        return self.__replace(
            _messages=(
                *self._messages,
                {"role": "user", "content": text, "kind": "text"},
            )
        )

    def assistant(self, text: str) -> MessageBuilder:
        """Append an assistant turn for few-shot priming.

        Args:
            text: The assistant message content.

        Returns:
            A new MessageBuilder with the assistant turn appended to _messages.
        """
        return self.__replace(
            _messages=(
                *self._messages,
                {"role": "assistant", "content": text, "kind": "text"},
            )
        )

    def max_tokens(self, n: int) -> MessageBuilder:
        """Override the maximum token count for this request.

        Args:
            n: The new upper bound on tokens the provider may generate.

        Returns:
            A new MessageBuilder with _max_tokens set to n.
        """
        return self.__replace(_max_tokens=n)

    def tools(self, *names: str) -> MessageBuilder:
        """Append tool names to offer in this and any inherited request.

        Names are registry keys (see register_tool() / Yokel.register_tools()),
        not Tool instances. Resolution against the registry happens at .send()
        time, not here.

        Args:
            names: Tool registry keys to append to the offered tool set.

        Returns:
            A new MessageBuilder with names appended to _tool_names.
        """
        return self.__replace(_tool_names=(*self._tool_names, *names))

    def send(self) -> Response:
        """Resolve tools and dispatch the current message list to the provider.

        Returns:
            A normalised Response with text, model, stop_reason, usage, and
            any requested tool calls.

        Raises:
            ValueError: _messages is empty — no user turn was added before send.
            UnknownToolError: A name passed to .tools() does not resolve
                against the tool registry.
            AuthError: Provider authentication rejected the request.
            ProviderError: Provider returned an upstream HTTP or API error.
        """
        if not self._messages:
            raise ValueError(
                "Cannot send: no messages have been added. "
                "Call .user() at least once before .send()."
            )

        response = self._provider.send(
            messages=self._messages,
            model=self._model,
            system=self._system,
            max_tokens=self._max_tokens,
            tools=self.__resolve_tools(),
        )
        object.__setattr__(self, "_last_response", response)
        object.__setattr__(self, "_tool_result_used", False)
        return response

    def tool_result(
        self, tool_use_id: str, content: str, *, is_error: bool = False
    ) -> MessageBuilder:
        """Submit a result for the single ToolCall from this instance's last .send().

        Appends the replayed assistant turn (via the provider's
        encode_assistant_turn(), tagged kind="tool_use") and a tool_result user
        turn (tagged kind="tool_result"). Single-shot: call .send() again to
        offer another tool call before calling this a second time, or use
        Conversation for open-ended multi-call exchanges.

        Args:
            tool_use_id: The ToolCall.id this result answers.
            content: The tool's result, as a string.
            is_error: Whether the tool execution failed.

        Returns:
            A new MessageBuilder with the replayed assistant turn and the
            tool_result turn appended to _messages.

        Raises:
            ValueError: tool_result() was already called on this instance, or
                the last .send() on this instance did not produce a Response
                with exactly one ToolCall.
        """
        if self._tool_result_used:
            raise ValueError(
                "tool_result() has already been called on this MessageBuilder. "
                "Call .send() again before calling tool_result() once more, or "
                "use Conversation for multi-call tool exchanges."
            )

        if self._last_response is None or len(self._last_response.tool_calls) != 1:
            raise ValueError(
                "tool_result() requires exactly one ToolCall on the Response "
                "from this instance's last .send(). Use Conversation for "
                "multi-call tool exchanges."
            )

        encoded = self._provider.encode_assistant_turn(self._last_response)
        result_block = {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }
        object.__setattr__(self, "_tool_result_used", True)
        return self.__replace(
            _messages=(
                *self._messages,
                {
                    "role": "assistant",
                    "content": encoded["content"],
                    "kind": "tool_use",
                },
                {"role": "user", "content": result_block, "kind": "tool_result"},
            )
        )

    def conversation(self) -> Conversation:
        """Create a mutable Conversation capturing this builder's configuration.

        The Conversation inherits model, system, max_tokens, tool names, the
        tool resolver, and any messages already in this builder as its initial
        history. Configuration cannot be changed after construction.

        Returns:
            A new Conversation ready for multi-turn use.
        """
        return Conversation(
            provider=self._provider,
            model=self._model,
            system=self._system,
            max_tokens=self._max_tokens,
            history=list(self._messages),
            tool_names=self._tool_names,
            tool_resolver=self._tool_resolver,
        )

    def __replace(self, **changes: Any) -> MessageBuilder:
        """dataclasses.replace(), resetting the per-instance send/tool_result state.

        Every request-building chain method goes through this so a derived
        copy never inherits _last_response/_tool_result_used from its source
        -- only the literal instance a .send() was called on can meaningfully
        call .tool_result() next.
        """
        return dataclasses.replace(
            self, _last_response=None, _tool_result_used=False, **changes
        )

    def __resolve_tools(self) -> tuple[Tool, ...]:
        """Resolve _tool_names against _tool_resolver, in order.

        Raises:
            UnknownToolError: A name does not resolve against the registry.
        """
        resolved: list[Tool] = []
        for name in self._tool_names:
            tool = self._tool_resolver(name)
            if tool is None:
                raise UnknownToolError(name)

            resolved.append(tool)

        return tuple(resolved)
