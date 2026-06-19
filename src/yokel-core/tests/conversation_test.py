"""Tests for _conversation.Conversation.

Covers: __init__, model, system, max_tokens, history, user, tool_result,
send, _reset.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
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
            text="assistant reply",
            model=model,
            stop_reason="end_turn",
            usage=Usage(input_tokens=2, output_tokens=3),
        )

    def encode_assistant_turn(self, response: Response) -> dict[str, Any]:
        return {"content": [{"type": "text", "text": response.text}]}


def _no_tools_resolver(name: str) -> Tool | None:
    """A tool resolver stub that never resolves anything."""
    return None


def _make_conversation(**overrides: Any) -> Conversation:
    """Return a Conversation with sensible defaults, overrideable per-test."""
    defaults: dict[str, Any] = {
        "provider": FakeProvider(),
        "model": "fake-model",
        "system": None,
        "max_tokens": 256,
        "history": None,
    }
    return Conversation(**{**defaults, **overrides})


class TestConversationInit:
    """Tests for Conversation.__init__."""

    def test_init_with_no_history_starts_empty(self) -> None:
        """Conversation initialised without history has an empty history list."""
        # Arrange & Act
        conv = _make_conversation()

        # Assert
        assert conv.history == [], "Expected empty history when none is provided"

    def test_init_with_history_seeds_history(self) -> None:
        """Conversation initialised with history seeds from the provided list."""
        # Arrange
        seed: list[dict[str, Any]] = [{"role": "user", "content": "Hello"}]

        # Act
        conv = _make_conversation(history=seed)

        # Assert
        assert conv.history == seed, "Expected history to equal the seeded messages"

    def test_init_copies_provided_history_list(self) -> None:
        """Mutating the seed list after construction does not affect history."""
        # Arrange
        seed: list[dict[str, Any]] = [{"role": "user", "content": "Hello"}]
        conv = _make_conversation(history=seed)

        # Act
        seed.append({"role": "assistant", "content": "Hi"})

        # Assert
        assert len(conv.history) == 1, (
            "Expected Conversation to hold an independent copy of the seed list"
        )


class TestConversationModel:
    """Tests for Conversation.model property."""

    def test_model_returns_value_from_constructor(self) -> None:
        """model property returns the model identifier passed at construction."""
        # Arrange & Act
        conv = _make_conversation(model="my-model")

        # Assert
        assert conv.model == "my-model", "Expected model to match the constructor arg"


class TestConversationSystem:
    """Tests for Conversation.system property."""

    def test_system_returns_none_when_not_set(self) -> None:
        """system property is None when no system prompt was given."""
        # Arrange & Act
        conv = _make_conversation(system=None)

        # Assert
        assert conv.system is None, "Expected system to be None"

    def test_system_returns_prompt_when_set(self) -> None:
        """system property returns the system prompt passed at construction."""
        # Arrange & Act
        conv = _make_conversation(system="Be concise.")

        # Assert
        assert conv.system == "Be concise.", (
            "Expected system to match the constructor arg"
        )


class TestConversationMaxTokens:
    """Tests for Conversation.max_tokens property."""

    def test_max_tokens_returns_value_from_constructor(self) -> None:
        """max_tokens property returns the value passed at construction."""
        # Arrange & Act
        conv = _make_conversation(max_tokens=512)

        # Assert
        assert conv.max_tokens == 512, (
            "Expected max_tokens to match the constructor arg"
        )


class TestConversationHistory:
    """Tests for Conversation.history property."""

    def test_history_returns_shallow_copy(self) -> None:
        """history returns a new list object, not a reference to the internal list."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        h1 = conv.history
        h2 = conv.history

        # Assert
        assert h1 is not h2, (
            "Expected each .history access to return a distinct list object"
        )

    def test_history_mutation_does_not_affect_conversation(self) -> None:
        """Mutating the returned history list does not change Conversation state."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        snapshot = conv.history
        snapshot.append({"role": "user", "content": "Injected"})

        # Assert
        assert len(conv.history) == 1, (
            "Expected internal history to be unaffected by mutation of the copy"
        )


class TestConversationUser:
    """Tests for Conversation.user."""

    def test_user_appends_user_turn(self) -> None:
        """user() appends a user-role dict tagged kind='text' to history."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.user("Hello")

        # Assert
        assert conv.history == [{"role": "user", "content": "Hello", "kind": "text"}], (
            "Expected a single user turn in history"
        )

    def test_user_returns_self(self) -> None:
        """user() returns the same Conversation instance for chaining."""
        # Arrange
        conv = _make_conversation()

        # Act
        result = conv.user("Hello")

        # Assert
        assert result is conv, "Expected user() to return self for in-place mutation"

    def test_user_called_twice_appends_both_turns(self) -> None:
        """user() called twice appends both messages in order."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.user("First")
        conv.user("Second")

        # Assert
        assert conv.history == [
            {"role": "user", "content": "First", "kind": "text"},
            {"role": "user", "content": "Second", "kind": "text"},
        ], "Expected both user turns in insertion order"

    def test_user_enables_send_chaining(self) -> None:
        """conv.user('msg').send() works as a single chained expression."""
        # Arrange
        conv = _make_conversation()

        # Act
        result = conv.user("Hello").send()

        # Assert
        assert isinstance(result, Response), (
            "Expected .user().send() chain to return a Response"
        )


class TestConversationToolResult:
    """Tests for Conversation.tool_result."""

    def test_tool_result_appends_user_turn_with_block_list(self) -> None:
        """tool_result() appends a user turn whose content is a list of blocks."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.tool_result("toolu_1", "22C")

        # Assert
        assert conv.history == [
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "toolu_1",
                        "content": "22C",
                        "is_error": False,
                    }
                ],
                "kind": "tool_result",
            }
        ], "Expected a single tool_result turn with one block"

    def test_tool_result_returns_self(self) -> None:
        """tool_result() returns the same Conversation instance for chaining."""
        # Arrange
        conv = _make_conversation()

        # Act
        result = conv.tool_result("toolu_1", "22C")

        # Assert
        assert result is conv, "Expected tool_result() to return self"

    def test_tool_result_with_is_error_sets_flag(self) -> None:
        """tool_result(is_error=True) sets is_error on the result block."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.tool_result("toolu_1", "boom", is_error=True)

        # Assert
        assert conv.history[-1]["content"][0]["is_error"] is True, (
            "Expected is_error=True to propagate to the result block"
        )

    def test_multiple_tool_results_accumulate_into_one_turn(self) -> None:
        """Multiple tool_result() calls before send() land in a single user turn."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.tool_result("toolu_1", "22C")
        conv.tool_result("toolu_2", "Sunny")

        # Assert
        assert len(conv.history) == 1, (
            "Expected both results to accumulate into a single history turn"
        )
        assert conv.history[0]["content"] == [
            {
                "type": "tool_result",
                "tool_use_id": "toolu_1",
                "content": "22C",
                "is_error": False,
            },
            {
                "type": "tool_result",
                "tool_use_id": "toolu_2",
                "content": "Sunny",
                "is_error": False,
            },
        ], "Expected both blocks present, in call order, on the same turn"

    def test_tool_result_after_unrelated_user_turn_starts_new_turn(self) -> None:
        """tool_result() after a plain user turn starts a separate turn."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        conv.tool_result("toolu_1", "22C")

        # Assert
        assert len(conv.history) == 2, "Expected the user turn and a new tool turn"
        assert conv.history[0]["kind"] == "text"
        assert conv.history[1]["kind"] == "tool_result"

    def test_tool_result_enables_send_chaining(self) -> None:
        """conv.tool_result(...).send() works as the last turn is a user turn."""
        # Arrange
        conv = _make_conversation()
        conv.tool_result("toolu_1", "22C")

        # Act
        result = conv.send()

        # Assert
        assert isinstance(result, Response), (
            "Expected a tool_result turn to satisfy the user-turn precondition"
        )


class TestConversationToolRoundTrip:
    """Tests for a full tool round-trip, per the design's Problem Statement example."""

    def test_full_round_trip_yields_final_text_response(self) -> None:
        """.user().send() -> tool_use -> .tool_result() -> .send() -> final text."""
        # Arrange
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        tool_use_response = Response(
            text="Let me check.",
            model="m",
            stop_reason="tool_use",
            usage=Usage(0, 0),
            tool_calls=(call,),
        )
        final_response = Response(
            text="It's 22C in Paris.",
            model="m",
            stop_reason="end_turn",
            usage=Usage(0, 0),
        )
        provider = MagicMock(spec=ProviderInterface)
        provider.send.side_effect = [tool_use_response, final_response]
        provider.encode_assistant_turn.side_effect = [
            {
                "content": [
                    {"type": "text", "text": "Let me check."},
                    {
                        "type": "tool_use",
                        "id": "toolu_1",
                        "name": "get_weather",
                        "input": {"city": "Paris"},
                    },
                ]
            },
            {"content": [{"type": "text", "text": "It's 22C in Paris."}]},
        ]
        conv = _make_conversation(provider=provider)

        # Act
        first = conv.user("What's the weather in Paris?").send()
        assert first.stop_reason == "tool_use", (
            "Expected the first send() to request a tool call"
        )
        for tool_call in first.tool_calls:
            conv.tool_result(tool_call.id, "22C")

        second = conv.send()

        # Assert
        assert second is final_response, (
            "Expected the second send() to return the final text Response"
        )
        assert second.stop_reason == "end_turn", (
            "Expected the round trip to end on a plain text response"
        )
        assert [turn["kind"] for turn in conv.history] == [
            "text",
            "tool_use",
            "tool_result",
            "text",
        ], "Expected turns tagged: user text, replayed tool_use, tool_result, text"


class TestConversationSend:
    """Tests for Conversation.send."""

    def test_send_with_user_turn_calls_provider(self) -> None:
        """send() dispatches to the provider and returns its Response."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        expected = Response(
            text="reply", model="fake", stop_reason="end_turn", usage=Usage(1, 1)
        )
        provider.send.return_value = expected
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "reply"}]
        }
        conv = _make_conversation(provider=provider)
        conv.user("Hello")

        # Act
        result = conv.send()

        # Assert
        assert result is expected, "Expected send() to return the provider's Response"

    def test_send_passes_correct_args_to_provider(self) -> None:
        """send() forwards messages, model, system, max_tokens, and tools."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "ok"}]
        }
        conv = _make_conversation(
            provider=provider,
            model="test-model",
            system="Be helpful.",
            max_tokens=128,
        )
        conv.user("Hi")

        # Act
        conv.send()

        # Assert
        provider.send.assert_called_once_with(
            messages=({"role": "user", "content": "Hi", "kind": "text"},),
            model="test-model",
            system="Be helpful.",
            max_tokens=128,
            tools=(),
        )

    def test_send_appends_assistant_turn_to_history(self) -> None:
        """send() appends the re-encoded assistant turn after the call."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        conv.send()

        # Assert
        assert conv.history[-1] == {
            "role": "assistant",
            "content": [{"type": "text", "text": "assistant reply"}],
            "kind": "text",
        }, "Expected the re-encoded assistant turn to be appended after send()"

    def test_send_tags_kind_tool_use_when_response_has_tool_calls(self) -> None:
        """send() tags the appended assistant turn kind='tool_use' on tool calls."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        provider.send.return_value = Response(
            text="Let me check.",
            model="m",
            stop_reason="tool_use",
            usage=Usage(0, 0),
            tool_calls=(call,),
        )
        provider.encode_assistant_turn.return_value = {
            "content": [
                {"type": "text", "text": "Let me check."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_weather",
                    "input": {},
                },
            ]
        }
        conv = _make_conversation(provider=provider)
        conv.user("What's the weather in Paris?")

        # Act
        conv.send()

        # Assert
        assert conv.history[-1]["kind"] == "tool_use", (
            "Expected kind='tool_use' when the response carries tool_calls"
        )

    def test_send_calls_encode_assistant_turn_with_response(self) -> None:
        """send() re-encodes the assistant turn via provider.encode_assistant_turn."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        expected = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        provider.send.return_value = expected
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "ok"}]
        }
        conv = _make_conversation(provider=provider)
        conv.user("Hi")

        # Act
        conv.send()

        # Assert
        provider.encode_assistant_turn.assert_called_once_with(expected)

    def test_send_appends_assistant_turn_on_max_tokens_stop_reason(self) -> None:
        """send() appends the assistant turn even when stop_reason is 'max_tokens'."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="truncated",
            model="m",
            stop_reason="max_tokens",
            usage=Usage(1, 1),
        )
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "truncated"}]
        }
        conv = _make_conversation(provider=provider)
        conv.user("Hello")

        # Act
        conv.send()

        # Assert
        assert conv.history[-1] == {
            "role": "assistant",
            "content": [{"type": "text", "text": "truncated"}],
            "kind": "text",
        }, "Expected assistant turn appended even on max_tokens truncation"

    def test_send_with_empty_history_raises_value_error(self) -> None:
        """send() raises ValueError when history is empty."""
        # Arrange
        conv = _make_conversation()

        # Act & Assert
        with pytest.raises(ValueError, match="history is empty"):
            conv.send()

    def test_send_when_last_message_is_not_user_raises_value_error(self) -> None:
        """send() raises ValueError when the last history entry is not a user turn."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")
        conv.send()  # appends assistant turn; last message is now assistant

        # Act & Assert
        with pytest.raises(ValueError, match="last message is not a user turn"):
            conv.send()

    def test_send_multi_turn_accumulates_full_history(self) -> None:
        """Multiple user/send cycles accumulate all turns in history."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.user("Turn one")
        conv.send()
        conv.user("Turn two")
        conv.send()

        # Assert
        assert len(conv.history) == 4, (
            "Expected 4 turns: user, assistant, user, assistant"
        )
        assert conv.history[0]["role"] == "user", "Expected first turn to be user"
        assert conv.history[1]["role"] == "assistant", (
            "Expected second turn to be assistant"
        )
        assert conv.history[2]["role"] == "user", "Expected third turn to be user"
        assert conv.history[3]["role"] == "assistant", (
            "Expected fourth turn to be assistant"
        )


class TestConversationSendToolResolution:
    """Tests for tool-name resolution in Conversation.send."""

    def test_send_with_no_tools_passes_empty_tuple(self) -> None:
        """send() without tool_names passes tools=() to the provider."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "ok"}]
        }
        conv = _make_conversation(provider=provider)
        conv.user("Hi")

        # Act
        conv.send()

        # Assert
        assert provider.send.call_args.kwargs["tools"] == (), (
            "Expected tools=() when no tool names were configured"
        )

    def test_send_resolves_tool_names_to_tool_instances(self) -> None:
        """send() resolves each tool_names entry via tool_resolver."""
        # Arrange
        provider = MagicMock(spec=ProviderInterface)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
        provider.encode_assistant_turn.return_value = {
            "content": [{"type": "text", "text": "ok"}]
        }
        weather_tool = Tool(name="get_weather", description="d", input_schema={})
        conv = _make_conversation(
            provider=provider,
            tool_names=("get_weather",),
            tool_resolver=lambda name: weather_tool if name == "get_weather" else None,
        )
        conv.user("Hi")

        # Act
        conv.send()

        # Assert
        assert provider.send.call_args.kwargs["tools"] == (weather_tool,), (
            "Expected the resolved Tool to be passed to provider.send"
        )

    def test_send_with_unresolvable_tool_name_raises_unknown_tool_error(self) -> None:
        """send() raises UnknownToolError when a tool name does not resolve."""
        # Arrange
        conv = _make_conversation(
            tool_names=("nonexistent",), tool_resolver=_no_tools_resolver
        )
        conv.user("Hi")

        # Act & Assert
        with pytest.raises(UnknownToolError) as exc_info:
            conv.send()

        assert exc_info.value.tool_name == "nonexistent", (
            "Expected UnknownToolError.tool_name to equal the unresolved name"
        )


class TestConversationReset:
    """Tests for Conversation._reset."""

    def test_reset_clears_history(self) -> None:
        """_reset() empties the conversation history."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        conv._reset()

        # Assert
        assert conv.history == [], "Expected history to be empty after _reset()"

    def test_reset_allows_send_after_clear(self) -> None:
        """After _reset(), send() works again once a new user turn is added."""
        # Arrange
        conv = _make_conversation()
        conv.user("First").send()
        conv._reset()
        conv.user("Second")

        # Act
        result = conv.send()

        # Assert
        assert isinstance(result, Response), (
            "Expected a valid Response after resetting and re-sending"
        )
