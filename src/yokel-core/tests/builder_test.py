"""Tests for MessageBuilder: system, user, assistant, max_tokens, send, conversation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from yokel._builder import MessageBuilder
from yokel._conversation import Conversation
from yokel.core.errors import UnknownToolError
from yokel.core.models import Response, Tool, ToolCall, Usage
from yokel.providers import ProviderInterface


class FakeProvider(ProviderInterface):
    """Minimal ProviderInterface stub that returns a canned Response."""

    default_max_tokens: int = 1024

    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
        *,
        tools: tuple[Any, ...] = (),
    ) -> Response:
        return Response(
            text="ok",
            model=model,
            stop_reason="end_turn",
            usage=Usage(input_tokens=1, output_tokens=1),
        )

    def encode_assistant_turn(self, response: Response) -> dict[str, Any]:
        return {"text": response.text}


def _no_tools_resolver(name: str) -> Tool | None:
    """A tool resolver stub that never resolves anything."""
    return None


def _make_builder(**overrides: Any) -> MessageBuilder:
    """Return a minimal MessageBuilder with sensible defaults."""
    defaults: dict[str, Any] = {
        "_provider": FakeProvider(),
        "_model": "fake-model",
        "_max_tokens": 256,
        "_system": None,
        "_messages": (),
        "_tool_resolver": _no_tools_resolver,
    }
    return MessageBuilder(**{**defaults, **overrides})


class TestMessageBuilderSystem:
    """Tests for MessageBuilder.system."""

    def test_system_with_text_sets_system_field(self) -> None:
        """system() returns a new builder with _system set to the given text."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.system("You are helpful.")

        # Assert
        assert result._system == "You are helpful.", (
            "Expected _system to be set to the provided text"
        )

    def test_system_does_not_mutate_original_builder(self) -> None:
        """system() leaves the original builder's _system unchanged."""
        # Arrange
        builder = _make_builder()

        # Act
        builder.system("Some prompt")

        # Assert
        assert builder._system is None, (
            "Expected original builder._system to remain None after system() call"
        )

    def test_system_called_twice_keeps_last_value(self) -> None:
        """Calling system() twice replaces the previous value."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.system("First").system("Second")

        # Assert
        assert result._system == "Second", (
            "Expected the last system() call to overwrite the previous value"
        )


class TestMessageBuilderUser:
    """Tests for MessageBuilder.user."""

    def test_user_appends_user_message(self) -> None:
        """user() appends a user-role dict to _messages."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.user("Hello")

        # Assert
        assert result._messages == (
            {"role": "user", "content": "Hello", "kind": "text"},
        ), "Expected a single user message dict in _messages"

    def test_user_does_not_mutate_original_builder(self) -> None:
        """user() leaves the original builder's _messages unchanged."""
        # Arrange
        builder = _make_builder()

        # Act
        builder.user("Hello")

        # Assert
        assert builder._messages == (), (
            "Expected original builder._messages to remain empty after user() call"
        )

    def test_user_called_twice_appends_both_messages(self) -> None:
        """user() called twice produces a tuple with both messages in order."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.user("First").user("Second")

        # Assert
        assert result._messages == (
            {"role": "user", "content": "First", "kind": "text"},
            {"role": "user", "content": "Second", "kind": "text"},
        ), "Expected two user messages in order"


class TestMessageBuilderAssistant:
    """Tests for MessageBuilder.assistant."""

    def test_assistant_appends_assistant_message(self) -> None:
        """assistant() appends an assistant-role dict to _messages."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.assistant("I am ready.")

        # Assert
        assert result._messages == (
            {"role": "assistant", "content": "I am ready.", "kind": "text"},
        ), "Expected a single assistant message dict in _messages"

    def test_assistant_does_not_mutate_original_builder(self) -> None:
        """assistant() leaves the original builder's _messages unchanged."""
        # Arrange
        builder = _make_builder()

        # Act
        builder.assistant("Hello")

        # Assert
        assert builder._messages == (), (
            "Expected original builder._messages to remain empty after assistant() call"
        )

    def test_assistant_interleaved_with_user_preserves_order(self) -> None:
        """assistant() and user() calls are appended in the order they are called."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.user("Q").assistant("A").user("Follow-up")

        # Assert
        assert result._messages == (
            {"role": "user", "content": "Q", "kind": "text"},
            {"role": "assistant", "content": "A", "kind": "text"},
            {"role": "user", "content": "Follow-up", "kind": "text"},
        ), "Expected messages in the exact order they were added"


class TestMessageBuilderMaxTokens:
    """Tests for MessageBuilder.max_tokens."""

    def test_max_tokens_overrides_existing_value(self) -> None:
        """max_tokens() returns a new builder with _max_tokens replaced."""
        # Arrange
        builder = _make_builder(_max_tokens=256)

        # Act
        result = builder.max_tokens(512)

        # Assert
        assert result._max_tokens == 512, "Expected _max_tokens to be updated to 512"

    def test_max_tokens_does_not_mutate_original_builder(self) -> None:
        """max_tokens() leaves the original builder's _max_tokens unchanged."""
        # Arrange
        builder = _make_builder(_max_tokens=256)

        # Act
        builder.max_tokens(9999)

        # Assert
        assert builder._max_tokens == 256, (
            "Expected original builder._max_tokens to remain 256"
        )


class TestMessageBuilderSend:
    """Tests for MessageBuilder.send."""

    def test_send_with_messages_calls_provider(self) -> None:
        """send() dispatches to the provider and returns its Response."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        expected = Response(
            text="hi", model="fake", stop_reason="end_turn", usage=Usage(1, 1)
        )
        provider.send.return_value = expected
        builder = _make_builder(
            _provider=provider,
            _messages=({"role": "user", "content": "Hello"},),
        )

        # Act
        result = builder.send()

        # Assert
        assert result is expected, "Expected send() to return the provider's Response"

    def test_send_passes_correct_args_to_provider(self) -> None:
        """send() forwards model, system, max_tokens, and messages to provider.send."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        messages: tuple[dict[str, str], ...] = ({"role": "user", "content": "Hi"},)
        builder = _make_builder(
            _provider=provider,
            _model="test-model",
            _max_tokens=128,
            _system="Be concise.",
            _messages=messages,
        )

        # Act
        builder.send()

        # Assert
        provider.send.assert_called_once_with(
            messages=messages,
            model="test-model",
            system="Be concise.",
            max_tokens=128,
            tools=(),
        )

    def test_send_with_empty_messages_raises_value_error(self) -> None:
        """send() raises ValueError when _messages is empty."""
        # Arrange
        builder = _make_builder(_messages=())

        # Act & Assert
        with pytest.raises(ValueError, match="no messages have been added"):
            builder.send()

    def test_send_branching_does_not_share_state(self) -> None:
        """Two builders branched from the same base send independently."""
        # Arrange
        base = _make_builder()
        b1 = base.user("Question one")
        b2 = base.user("Question two")

        # Act
        r1 = b1.send()
        r2 = b2.send()

        # Assert
        assert r1 is not r2, "Expected independent Response objects for each branch"
        assert b1._messages != b2._messages, (
            "Expected each branch to have distinct _messages"
        )


class TestMessageBuilderConversation:
    """Tests for MessageBuilder.conversation."""

    def test_conversation_returns_conversation_instance(self) -> None:
        """conversation() returns a Conversation object."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.conversation()

        # Assert
        assert isinstance(result, Conversation), (
            "Expected conversation() to return a Conversation instance"
        )

    def test_conversation_inherits_model(self) -> None:
        """conversation() passes the builder's model to the Conversation."""
        # Arrange
        builder = _make_builder(_model="test-model-x")

        # Act
        result = builder.conversation()

        # Assert
        assert result.model == "test-model-x", (
            "Expected Conversation.model to equal the builder's _model"
        )

    def test_conversation_inherits_system(self) -> None:
        """conversation() passes the builder's system prompt to the Conversation."""
        # Arrange
        builder = _make_builder(_system="Be precise.")

        # Act
        result = builder.conversation()

        # Assert
        assert result.system == "Be precise.", (
            "Expected Conversation.system to equal the builder's _system"
        )

    def test_conversation_inherits_max_tokens(self) -> None:
        """conversation() passes the builder's max_tokens to the Conversation."""
        # Arrange
        builder = _make_builder(_max_tokens=512)

        # Act
        result = builder.conversation()

        # Assert
        assert result.max_tokens == 512, (
            "Expected Conversation.max_tokens to equal the builder's _max_tokens"
        )

    def test_conversation_inherits_existing_messages_as_history(self) -> None:
        """conversation() seeds Conversation history from the builder's _messages."""
        # Arrange
        builder = _make_builder(
            _messages=({"role": "user", "content": "Seed message"},)
        )

        # Act
        result = builder.conversation()

        # Assert
        assert result.history == [{"role": "user", "content": "Seed message"}], (
            "Expected Conversation.history to contain the builder's existing messages"
        )

    def test_conversation_does_not_mutate_original_builder(self) -> None:
        """conversation() leaves the original builder's _messages unchanged."""
        # Arrange
        builder = _make_builder(_messages=({"role": "user", "content": "Hi"},))

        # Act
        conv = builder.conversation()
        conv.user("New message")

        # Assert
        assert builder._messages == ({"role": "user", "content": "Hi"},), (
            "Expected builder._messages to be unchanged after mutating the Conversation"
        )

    def test_conversation_inherits_tool_names_and_resolver(self) -> None:
        """conversation() passes _tool_names and _tool_resolver through."""
        # Arrange
        weather_tool = Tool(name="get_weather", description="d", input_schema={})
        builder = _make_builder(
            _tool_names=("get_weather",),
            _tool_resolver=lambda name: weather_tool if name == "get_weather" else None,
        )

        # Act
        result = builder.conversation()

        # Assert
        tool_names = getattr(result, "_Conversation__tool_names")
        tool_resolver = getattr(result, "_Conversation__tool_resolver")
        assert tool_names == ("get_weather",), (
            "Expected Conversation to receive the builder's _tool_names"
        )
        assert tool_resolver("get_weather") is weather_tool, (
            "Expected Conversation to receive the builder's _tool_resolver"
        )


class TestMessageBuilderTools:
    """Tests for MessageBuilder.tools."""

    def test_tools_appends_names(self) -> None:
        """tools() returns a new builder with names appended to _tool_names."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.tools("get_weather", "search")

        # Assert
        assert result._tool_names == ("get_weather", "search"), (
            "Expected both names appended to _tool_names"
        )

    def test_tools_does_not_mutate_original_builder(self) -> None:
        """tools() leaves the original builder's _tool_names unchanged."""
        # Arrange
        builder = _make_builder()

        # Act
        builder.tools("get_weather")

        # Assert
        assert builder._tool_names == (), (
            "Expected original builder._tool_names to remain empty after tools() call"
        )

    def test_tools_called_twice_accumulates_names(self) -> None:
        """tools() called twice accumulates names from both calls."""
        # Arrange
        builder = _make_builder()

        # Act
        result = builder.tools("get_weather").tools("search")

        # Assert
        assert result._tool_names == ("get_weather", "search"), (
            "Expected names from both calls to accumulate in order"
        )


class TestMessageBuilderSendToolResolution:
    """Tests for tool-name resolution in MessageBuilder.send."""

    def test_send_with_no_tools_passes_empty_tuple(self) -> None:
        """send() without .tools() passes tools=() to the provider."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        builder = _make_builder(
            _provider=provider, _messages=({"role": "user", "content": "Hi"},)
        )

        # Act
        builder.send()

        # Assert
        assert provider.send.call_args.kwargs["tools"] == (), (
            "Expected tools=() when no tool names were added"
        )

    def test_send_resolves_tool_names_to_tool_instances(self) -> None:
        """send() resolves each _tool_names entry via _tool_resolver."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        weather_tool = Tool(name="get_weather", description="d", input_schema={})
        builder = _make_builder(
            _provider=provider,
            _messages=({"role": "user", "content": "Hi"},),
            _tool_resolver=lambda name: weather_tool if name == "get_weather" else None,
        ).tools("get_weather")

        # Act
        builder.send()

        # Assert
        assert provider.send.call_args.kwargs["tools"] == (weather_tool,), (
            "Expected the resolved Tool to be passed to provider.send"
        )

    def test_send_with_unresolvable_tool_name_raises_unknown_tool_error(self) -> None:
        """send() raises UnknownToolError when a tool name does not resolve."""
        # Arrange
        builder = _make_builder(_messages=({"role": "user", "content": "Hi"},)).tools(
            "nonexistent"
        )

        # Act & Assert
        with pytest.raises(UnknownToolError) as exc_info:
            builder.send()

        assert exc_info.value.tool_name == "nonexistent", (
            "Expected UnknownToolError.tool_name to equal the unresolved name"
        )


class TestMessageBuilderToolResult:
    """Tests for MessageBuilder.tool_result."""

    def _make_builder_after_send(
        self, *, tool_calls: tuple[ToolCall, ...]
    ) -> tuple[MessageBuilder, MagicMock]:
        """Return (builder, provider) where builder.send() has already run."""
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="Let me check.",
            model="m",
            stop_reason="tool_use" if tool_calls else "end_turn",
            usage=Usage(0, 0),
            tool_calls=tool_calls,
        )
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "Let me check."}]
        }
        builder = _make_builder(
            _provider=provider, _messages=({"role": "user", "content": "Hi"},)
        )
        builder.send()
        return builder, provider

    def test_tool_result_appends_assistant_and_result_turns(self) -> None:
        """tool_result() appends the replayed assistant turn and a result turn."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        builder, provider = self._make_builder_after_send(tool_calls=(call,))

        # Act
        result = builder.tool_result("toolu_1", "22C")

        # Assert
        assert result._messages == (
            {"role": "user", "content": "Hi"},
            {
                "role": "assistant",
                "content": [{"type": "text", "text": "Let me check."}],
                "kind": "tool_use",
            },
            {
                "role": "user",
                "content": {
                    "type": "tool_result",
                    "tool_use_id": "toolu_1",
                    "content": "22C",
                    "is_error": False,
                },
                "kind": "tool_result",
            },
        ), "Expected the replayed assistant turn and the tool_result turn appended"

    def test_tool_result_calls_encode_assistant_turn_with_prior_response(self) -> None:
        """tool_result() calls provider.encode_assistant_turn with the last Response."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        builder, provider = self._make_builder_after_send(tool_calls=(call,))

        # Act
        builder.tool_result("toolu_1", "22C")

        # Assert
        sent_response = provider.encode_assistant_turn.call_args.args[0]
        assert sent_response.tool_calls == (call,), (
            "Expected encode_assistant_turn to be called with the prior Response"
        )

    def test_tool_result_with_is_error_sets_flag(self) -> None:
        """tool_result(is_error=True) sets is_error on the result block."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        builder, _ = self._make_builder_after_send(tool_calls=(call,))

        # Act
        result = builder.tool_result("toolu_1", "boom", is_error=True)

        # Assert
        assert result._messages[-1]["content"]["is_error"] is True, (
            "Expected is_error=True to propagate to the result block"
        )

    def test_tool_result_without_prior_send_raises_value_error(self) -> None:
        """tool_result() before any .send() raises ValueError."""
        # Arrange
        builder = _make_builder()

        # Act & Assert
        with pytest.raises(ValueError, match="requires exactly one ToolCall"):
            builder.tool_result("toolu_1", "22C")

    def test_tool_result_with_no_prior_tool_calls_raises_value_error(self) -> None:
        """tool_result() raises ValueError when the prior Response had no ToolCalls."""
        # Arrange
        builder, _ = self._make_builder_after_send(tool_calls=())

        # Act & Assert
        with pytest.raises(ValueError, match="requires exactly one ToolCall"):
            builder.tool_result("toolu_1", "22C")

    def test_tool_result_with_multiple_prior_tool_calls_raises_value_error(
        self,
    ) -> None:
        """tool_result() raises ValueError when the prior Response had >1 ToolCall."""
        # Arrange
        calls = (
            ToolCall(id="toolu_1", name="get_weather", input={}),
            ToolCall(id="toolu_2", name="search", input={}),
        )
        builder, _ = self._make_builder_after_send(tool_calls=calls)

        # Act & Assert
        with pytest.raises(ValueError, match="requires exactly one ToolCall"):
            builder.tool_result("toolu_1", "22C")

    def test_tool_result_called_twice_on_same_instance_raises_value_error(
        self,
    ) -> None:
        """Calling tool_result() twice on the same builder instance raises."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        builder, _ = self._make_builder_after_send(tool_calls=(call,))
        builder.tool_result("toolu_1", "22C")

        # Act & Assert
        with pytest.raises(ValueError, match="already been called"):
            builder.tool_result("toolu_1", "second call")

    def test_tool_result_returned_builder_allows_a_new_send_cycle(self) -> None:
        """The builder returned by tool_result() can call tool_result() is reset."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        builder, _ = self._make_builder_after_send(tool_calls=(call,))

        # Act
        result = builder.tool_result("toolu_1", "22C")

        # Assert
        assert result._last_response is None, (
            "Expected the returned builder to start with no cached _last_response"
        )
        assert result._tool_result_used is False, (
            "Expected the returned builder to start with _tool_result_used reset"
        )
