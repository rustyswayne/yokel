"""Tests for _conversation.Conversation.

Covers: __init__, model, system, max_tokens, history, user, send, _reset.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from yokel._conversation import Conversation
from yokel.core.models import Response, Usage
from yokel.providers import Provider


class FakeProvider(Provider):
    """Minimal Provider stub that returns a canned Response."""

    default_max_tokens: int = 1024

    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
    ) -> Response:
        return Response(
            text="assistant reply",
            model=model,
            stop_reason="end_turn",
            usage=Usage(input_tokens=2, output_tokens=3),
        )


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
        seed: list[dict[str, str]] = [{"role": "user", "content": "Hello"}]

        # Act
        conv = _make_conversation(history=seed)

        # Assert
        assert conv.history == seed, "Expected history to equal the seeded messages"

    def test_init_copies_provided_history_list(self) -> None:
        """Mutating the seed list after construction does not affect history."""
        # Arrange
        seed: list[dict[str, str]] = [{"role": "user", "content": "Hello"}]
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
        """user() appends a user-role dict to history."""
        # Arrange
        conv = _make_conversation()

        # Act
        conv.user("Hello")

        # Assert
        assert conv.history == [{"role": "user", "content": "Hello"}], (
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
            {"role": "user", "content": "First"},
            {"role": "user", "content": "Second"},
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


class TestConversationSend:
    """Tests for Conversation.send."""

    def test_send_with_user_turn_calls_provider(self) -> None:
        """send() dispatches to the provider and returns its Response."""
        # Arrange
        provider = MagicMock(spec=Provider)
        expected = Response(
            text="reply", model="fake", stop_reason="end_turn", usage=Usage(1, 1)
        )
        provider.send.return_value = expected
        conv = _make_conversation(provider=provider)
        conv.user("Hello")

        # Act
        result = conv.send()

        # Assert
        assert result is expected, "Expected send() to return the provider's Response"

    def test_send_passes_correct_args_to_provider(self) -> None:
        """send() forwards messages, model, system, and max_tokens to provider."""
        # Arrange
        provider = MagicMock(spec=Provider)
        provider.send.return_value = Response(
            text="ok", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )
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
            messages=({"role": "user", "content": "Hi"},),
            model="test-model",
            system="Be helpful.",
            max_tokens=128,
        )

    def test_send_appends_assistant_turn_to_history(self) -> None:
        """send() appends the assistant response text to history after the call."""
        # Arrange
        conv = _make_conversation()
        conv.user("Hello")

        # Act
        conv.send()

        # Assert
        assert conv.history[-1] == {
            "role": "assistant",
            "content": "assistant reply",
        }, "Expected the assistant turn to be appended after send()"

    def test_send_appends_assistant_turn_on_max_tokens_stop_reason(self) -> None:
        """send() appends the assistant turn even when stop_reason is 'max_tokens'."""
        # Arrange
        provider = MagicMock(spec=Provider)
        provider.send.return_value = Response(
            text="truncated",
            model="m",
            stop_reason="max_tokens",
            usage=Usage(1, 1),
        )
        conv = _make_conversation(provider=provider)
        conv.user("Hello")

        # Act
        conv.send()

        # Assert
        assert conv.history[-1] == {
            "role": "assistant",
            "content": "truncated",
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
