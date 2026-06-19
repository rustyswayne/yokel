"""Tests for AnthropicProvider: __init__, conf, send."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest
from anthropic.types import (
    Message as SdkMessage,
    TextBlock as SdkTextBlock,
    ToolUseBlock as SdkToolUseBlock,
    Usage as SdkUsage,
)
from yokel.anthropic._provider import AnthropicProvider
from yokel.core.configuration.manager import ConfigurationSection
from yokel.core.errors import AuthError, ProviderError
from yokel.core.models import Response, Tool, ToolCall, Usage


def _make_text_block(text: str) -> Any:
    """Build a spec'd MagicMock standing in for an anthropic TextBlock."""
    block = MagicMock(spec=SdkTextBlock)
    block.type = "text"
    block.text = text
    return block


def _make_tool_use_block(
    *,
    block_id: str = "toolu_1",
    name: str = "get_weather",
    block_input: dict[str, Any] | None = None,
) -> Any:
    """Build a spec'd MagicMock standing in for an anthropic ToolUseBlock."""
    block = MagicMock(spec=SdkToolUseBlock)
    block.type = "tool_use"
    block.id = block_id
    block.name = name
    block.input = block_input if block_input is not None else {"city": "Paris"}
    return block


def _make_message(
    *,
    text: str = "hi",
    model: str = "claude-opus-4-8",
    stop_reason: str = "end_turn",
    extra_blocks: list[Any] | None = None,
) -> Any:
    """Build a spec'd MagicMock standing in for an anthropic.types.Message."""
    message = MagicMock(spec=SdkMessage)
    message.content = [_make_text_block(text), *(extra_blocks or [])]
    message.model = model
    message.stop_reason = stop_reason
    message.usage = MagicMock(spec=SdkUsage)
    message.usage.input_tokens = 3
    message.usage.output_tokens = 5
    return message


def _make_message_response(
    *, text: str, tool_calls: tuple[ToolCall, ...] = ()
) -> Response:
    """Build a yokel Response for encode_assistant_turn tests."""
    return Response(
        text=text,
        model="claude-opus-4-8",
        stop_reason="tool_use" if tool_calls else "end_turn",
        usage=Usage(input_tokens=1, output_tokens=1),
        tool_calls=tool_calls,
    )


def _status_error(
    error_cls: type[anthropic.APIStatusError], status_code: int
) -> anthropic.APIStatusError:
    """Build a real anthropic APIStatusError subclass instance for a given status."""
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request, json={"error": {}})
    return error_cls(message="boom", response=response, body={"error": {}})


class TestInit:
    """Tests for AnthropicProvider.__init__."""

    def test_init_with_explicit_api_key_constructs_client(self) -> None:
        """An explicit api_key resolves first and constructs the SDK client."""
        # Act
        provider = AnthropicProvider(api_key="sk-explicit")

        # Assert
        assert provider.conf == {"api_key": "sk-explicit"}, (
            "conf should expose the resolved api_key"
        )

    def test_init_with_resolver_used_before_value_store(self) -> None:
        """api_key_resolver() is tried before value_store."""
        # Arrange
        value_store = ConfigurationSection(
            "value_store", {"anthropic_api_key": "sk-from-store"}
        )

        # Act
        provider = AnthropicProvider(
            value_store, api_key_resolver=lambda: "sk-from-resolver"
        )

        # Assert
        assert provider.conf["api_key"] == "sk-from-resolver", (
            "resolver result should win over value_store"
        )

    def test_init_falls_back_to_value_store(self) -> None:
        """value_store.get('anthropic_api_key') is used when no resolver result."""
        # Arrange
        value_store = ConfigurationSection(
            "value_store", {"anthropic_api_key": "sk-from-store"}
        )

        # Act
        provider = AnthropicProvider(value_store, api_key_resolver=lambda: None)

        # Assert
        assert provider.conf["api_key"] == "sk-from-store", (
            "value_store should supply the key when the resolver returns None"
        )

    def test_init_falls_back_to_environment_variable(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ANTHROPIC_API_KEY env var is the last resolution step."""
        # Arrange
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-from-env")

        # Act
        provider = AnthropicProvider()

        # Assert
        assert provider.conf["api_key"] == "sk-from-env", (
            "env var should supply the key when nothing else resolves"
        )

    def test_init_raises_auth_error_when_nothing_resolves(self) -> None:
        """No api_key/resolver/value_store/env raises AuthError at construction."""
        # Act / Assert
        with pytest.raises(AuthError, match="No Anthropic API key resolved"):
            AnthropicProvider()

    def test_init_sets_default_max_tokens_to_4096(self) -> None:
        """default_max_tokens overrides the ABC default of 1024."""
        # Assert
        assert AnthropicProvider.default_max_tokens == 4096, (
            "AnthropicProvider must override default_max_tokens to 4096"
        )


class TestConf:
    """Tests for the AnthropicProvider.conf property."""

    def test_conf_setter_overrides_resolved_configuration(self) -> None:
        """conf is mutable -- a caller can override it after construction."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")

        # Act
        provider.conf = {"api_key": "sk-overridden"}

        # Assert
        assert provider.conf == {"api_key": "sk-overridden"}, (
            "conf setter should replace the stored configuration"
        )


class TestSend:
    """Tests for AnthropicProvider.send."""

    def test_send_returns_normalised_response(self) -> None:
        """send() translates the SDK Message into a yokel Response."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message(
            text="hello there"
        )

        # Act
        response = provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
        )

        # Assert
        assert response.text == "hello there", "Response.text should be the SDK text"
        assert response.model == "claude-opus-4-8", "Response.model should pass through"
        assert response.stop_reason == "end_turn", "stop_reason should pass through"
        assert response.usage.input_tokens == 3, "input_tokens should pass through"
        assert response.usage.output_tokens == 5, "output_tokens should pass through"

    def test_send_omits_system_key_when_none(self) -> None:
        """system=None must not appear in the create() call kwargs."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message()

        # Act
        provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
        )

        # Assert
        kwargs = provider._client.messages.create.call_args.kwargs
        assert "system" not in kwargs, "system key must be omitted when system is None"

    def test_send_includes_system_key_when_provided(self) -> None:
        """A non-None system prompt is passed through to create()."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message()

        # Act
        provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system="Be terse.",
            max_tokens=256,
        )

        # Assert
        kwargs = provider._client.messages.create.call_args.kwargs
        assert kwargs["system"] == "Be terse.", "system should be passed through"

    def test_send_with_authentication_error_raises_auth_error(self) -> None:
        """anthropic.AuthenticationError maps to AuthError."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.side_effect = _status_error(
            anthropic.AuthenticationError, 401
        )

        # Act / Assert
        with pytest.raises(AuthError):
            provider.send(
                messages=({"role": "user", "content": "hi"},),
                model="claude-opus-4-8",
                system=None,
                max_tokens=256,
            )

    def test_send_with_permission_denied_error_raises_auth_error(self) -> None:
        """anthropic.PermissionDeniedError maps to AuthError."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.side_effect = _status_error(
            anthropic.PermissionDeniedError, 403
        )

        # Act / Assert
        with pytest.raises(AuthError):
            provider.send(
                messages=({"role": "user", "content": "hi"},),
                model="claude-opus-4-8",
                system=None,
                max_tokens=256,
            )

    def test_send_with_other_api_status_error_raises_provider_error(self) -> None:
        """Any other anthropic.APIStatusError maps to ProviderError with status_code."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.side_effect = _status_error(
            anthropic.RateLimitError, 429
        )

        # Act / Assert
        with pytest.raises(ProviderError) as exc_info:
            provider.send(
                messages=({"role": "user", "content": "hi"},),
                model="claude-opus-4-8",
                system=None,
                max_tokens=256,
            )

        assert exc_info.value.status_code == 429, (
            "ProviderError.status_code should carry the SDK's HTTP status"
        )

    def test_send_with_connection_error_raises_provider_error_with_sentinel_zero(
        self,
    ) -> None:
        """anthropic.APIConnectionError maps to ProviderError(status_code=0, ...)."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
        provider._client.messages.create.side_effect = anthropic.APIConnectionError(
            request=request
        )

        # Act / Assert
        with pytest.raises(ProviderError) as exc_info:
            provider.send(
                messages=({"role": "user", "content": "hi"},),
                model="claude-opus-4-8",
                system=None,
                max_tokens=256,
            )

        assert exc_info.value.status_code == 0, (
            "APIConnectionError has no HTTP status -- sentinel must be 0"
        )

    def test_send_with_no_tools_omits_tools_key(self) -> None:
        """tools=() must not appear as a "tools" key in the create() call kwargs."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message()

        # Act
        provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
        )

        # Assert
        kwargs = provider._client.messages.create.call_args.kwargs
        assert "tools" not in kwargs, "tools key must be omitted when tools is empty"

    def test_send_with_tools_translates_to_sdk_shape(self) -> None:
        """Each Tool is translated to {name, description, input_schema}."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message()
        tool = Tool(
            name="get_weather",
            description="Look up the current weather for a city.",
            input_schema={"type": "object", "properties": {}},
        )

        # Act
        provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
            tools=(tool,),
        )

        # Assert
        kwargs = provider._client.messages.create.call_args.kwargs
        assert kwargs["tools"] == [
            {
                "name": "get_weather",
                "description": "Look up the current weather for a city.",
                "input_schema": {"type": "object", "properties": {}},
            }
        ], "Tool should translate to the SDK's {name, description, input_schema} shape"

    def test_send_with_tool_use_block_parses_into_tool_call(self) -> None:
        """A tool_use response block round-trips into ToolCall(id, name, input)."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        provider._client.messages.create.return_value = _make_message(
            stop_reason="tool_use",
            extra_blocks=[
                _make_tool_use_block(
                    block_id="toolu_1",
                    name="get_weather",
                    block_input={"city": "Paris"},
                )
            ],
        )

        # Act
        response = provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
        )

        # Assert
        assert response.tool_calls == (
            ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"}),
        ), "Expected the tool_use block to round-trip into a matching ToolCall"

    def test_send_populates_raw_content_with_unmodified_sdk_content(self) -> None:
        """raw_content carries the SDK response's content list verbatim."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        provider._client = MagicMock()
        message = _make_message()
        provider._client.messages.create.return_value = message

        # Act
        response = provider.send(
            messages=({"role": "user", "content": "hi"},),
            model="claude-opus-4-8",
            system=None,
            max_tokens=256,
        )

        # Assert
        assert response.raw_content is message.content, (
            "raw_content should be the SDK response's content object, unmodified"
        )


class TestEncodeAssistantTurn:
    """Tests for AnthropicProvider.encode_assistant_turn."""

    def test_encode_assistant_turn_with_text_only_returns_text_block(self) -> None:
        """A text-only Response encodes to a single text content block."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        response = _make_message_response(text="hello there")

        # Act
        result = provider.encode_assistant_turn(response)

        # Assert
        assert result == {"content": [{"type": "text", "text": "hello there"}]}, (
            "Expected a single text block carrying the response's text"
        )

    def test_encode_assistant_turn_with_tool_calls_returns_tool_use_blocks(
        self,
    ) -> None:
        """Each ToolCall encodes to a tool_use block, in order, after the text block."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        response = _make_message_response(text="Let me check.", tool_calls=(call,))

        # Act
        result = provider.encode_assistant_turn(response)

        # Assert
        assert result == {
            "content": [
                {"type": "text", "text": "Let me check."},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_weather",
                    "input": {"city": "Paris"},
                },
            ]
        }, "Expected a leading text block followed by one tool_use block per call"

    def test_encode_assistant_turn_with_empty_text_omits_text_block(self) -> None:
        """A pure-tool-call Response (empty text) omits the leading text block."""
        # Arrange
        provider = AnthropicProvider(api_key="sk-explicit")
        call = ToolCall(id="toolu_1", name="get_weather", input={"city": "Paris"})
        response = _make_message_response(text="", tool_calls=(call,))

        # Act
        result = provider.encode_assistant_turn(response)

        # Assert
        assert result == {
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "get_weather",
                    "input": {"city": "Paris"},
                },
            ]
        }, "Expected no text block when response.text is empty"
