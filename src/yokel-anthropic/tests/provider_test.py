"""Tests for AnthropicProvider: __init__, conf, send."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import anthropic
import httpx
import pytest
from yokel.anthropic._provider import AnthropicProvider
from yokel.core.configuration.manager import ConfigurationSection
from yokel.core.errors import AuthError, ProviderError


def _make_message(
    *, text: str = "hi", model: str = "claude-opus-4-8", stop_reason: str = "end_turn"
) -> Any:
    """Build a MagicMock standing in for an anthropic.types.Message."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    message = MagicMock()
    message.content = [block]
    message.model = model
    message.stop_reason = stop_reason
    message.usage.input_tokens = 3
    message.usage.output_tokens = 5
    return message


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
