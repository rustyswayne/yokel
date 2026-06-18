"""Tests for MessageBuilder: system, user, assistant, max_tokens, send, conversation."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from yokel._builder import MessageBuilder
from yokel._conversation import Conversation
from yokel.core.models import Response, Usage
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
    ) -> Response:
        return Response(
            text="ok",
            model=model,
            stop_reason="end_turn",
            usage=Usage(input_tokens=1, output_tokens=1),
        )


def _make_builder(**overrides: Any) -> MessageBuilder:
    """Return a minimal MessageBuilder with sensible defaults."""
    defaults: dict[str, Any] = {
        "_provider": FakeProvider(),
        "_model": "fake-model",
        "_max_tokens": 256,
        "_system": None,
        "_messages": (),
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
        assert result._messages == ({"role": "user", "content": "Hello"},), (
            "Expected a single user message dict in _messages"
        )

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
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
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
        assert result._messages == ({"role": "assistant", "content": "I am ready."},), (
            "Expected a single assistant message dict in _messages"
        )

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
            {"role": "user", "content": "Q"},
            {"role": "assistant", "content": "A"},
            {"role": "user", "content": "Follow-up"},
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
