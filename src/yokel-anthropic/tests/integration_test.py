"""Optional live integration tests -- need a real API key."""

from __future__ import annotations

import importlib
import sys

import pytest
from yokel.anthropic._provider import AnthropicProvider
from yokel.api import Yokel
from yokel.core.models import Tool


class TestLiveSend:
    """Live test against the real Anthropic API. Excluded from the default CI run."""

    @pytest.mark.requires_api_key
    def test_send_against_live_api_returns_response(self) -> None:
        """A real send() call returns a populated Response."""
        # Arrange
        provider = AnthropicProvider()

        # Act
        response = provider.send(
            messages=({"role": "user", "content": "Say 'ok' and nothing else."},),
            model="claude-haiku-4-5",
            system=None,
            max_tokens=16,
        )

        # Assert
        assert response.text, "live response should contain generated text"


class TestLiveYokelSend:
    """Live test against the real Anthropic API through the Yokel public API."""

    @pytest.mark.requires_api_key
    def test_yokel_model_send_against_live_api_returns_response(self) -> None:
        """Yokel().model("claude-*") resolves AnthropicProvider via import-time
        registration, and .user(...).send() returns a populated Response.
        """
        # Arrange -- re-import to re-apply registration cleared by the
        # autouse reset_yokel_singleton_and_registry fixture
        sys.modules.pop("yokel.anthropic", None)
        importlib.import_module("yokel.anthropic")

        y = Yokel()
        builder = y.model("claude-haiku-4-5", max_tokens=16)
        assert isinstance(builder._provider, AnthropicProvider)

        # Act
        response = builder.user("Say 'ok' and nothing else.").send()

        # Assert
        assert response.text, "live response should contain generated text"


class TestLiveSendWithTools:
    """Live tool-use round trip against the real Anthropic API."""

    @pytest.mark.requires_api_key
    def test_send_with_tools_round_trips_to_final_text_response(self) -> None:
        """.send() -> tool_use -> encode_assistant_turn()/tool_result -> final text."""
        # Arrange
        provider = AnthropicProvider()
        get_weather = Tool(
            name="get_weather",
            description="Look up the current weather for a city.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        )
        messages: tuple[dict[str, object], ...] = (
            {
                "role": "user",
                "content": "What's the weather in Paris? Use the tool.",
            },
        )

        # Act
        first = provider.send(
            messages=messages,
            model="claude-haiku-4-5",
            system=None,
            max_tokens=256,
            tools=(get_weather,),
        )

        # Assert
        assert first.stop_reason == "tool_use", (
            "expected the model to request the get_weather tool"
        )
        assert first.tool_calls, "expected at least one ToolCall on the response"

        # Act -- replay the assistant turn and submit a result
        call = first.tool_calls[0]
        encoded = provider.encode_assistant_turn(first)
        messages = (
            *messages,
            {"role": "assistant", "content": encoded["content"]},
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": call.id,
                        "content": "22C and sunny",
                        "is_error": False,
                    }
                ],
            },
        )
        second = provider.send(
            messages=messages,
            model="claude-haiku-4-5",
            system=None,
            max_tokens=256,
            tools=(get_weather,),
        )

        # Assert
        assert second.text, "expected a final text response after the tool result"
