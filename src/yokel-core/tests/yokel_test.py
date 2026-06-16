"""Tests for _yokel.Yokel: __init__, conf, model, _resolve_provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from yokel._builder import MessageBuilder
from yokel._yokel import Yokel
from yokel.core.configuration.manager import ConfigurationManager
from yokel.core.errors import AuthError, UnknownModelError
from yokel.core.models import Response
from yokel.providers import Provider


class FakeProvider(Provider):
    """Minimal Provider stub for testing; raises NotImplementedError on send."""

    default_max_tokens: int = 512

    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
    ) -> Response:
        raise NotImplementedError


def _make_config(patterns: dict[str, str], provider: Any) -> ConfigurationManager:
    """Return a mocked ConfigurationManager wired to resolve patterns to provider."""
    plugins_mock = MagicMock()
    plugins_mock.build.return_value = patterns
    plugins_mock.activate.return_value = provider
    config = MagicMock(spec=ConfigurationManager)
    config.plugins = plugins_mock
    config.value_store = MagicMock()
    return config


class TestYokelInit:
    """Tests for Yokel.__init__."""

    def test_init_without_config_creates_default_manager(self) -> None:
        """Yokel() builds a default ConfigurationManager when config is None."""
        # Arrange & Act
        y = Yokel()

        # Assert
        assert isinstance(y.conf, ConfigurationManager), (
            "Expected a ConfigurationManager when no config is provided"
        )

    def test_init_with_config_uses_provided_manager(self) -> None:
        """Yokel(config=mgr) stores the supplied ConfigurationManager."""
        # Arrange
        config = ConfigurationManager()

        # Act
        y = Yokel(config=config)

        # Assert
        assert y.conf is config, (
            "Expected the provided ConfigurationManager to be stored"
        )


class TestYokelConf:
    """Tests for Yokel.conf."""

    def test_conf_returns_owned_configuration_manager(self) -> None:
        """conf exposes the ConfigurationManager owned by this instance."""
        # Arrange
        y = Yokel()

        # Act
        result = y.conf

        # Assert
        assert isinstance(result, ConfigurationManager), (
            "Expected conf to return a ConfigurationManager"
        )


class TestYokelModel:
    """Tests for Yokel.model."""

    def test_model_with_matching_pattern_returns_message_builder(self) -> None:
        """model() returns a MessageBuilder when a provider pattern matches."""
        # Arrange
        provider = FakeProvider()
        config = _make_config({"fake-*": "fake_module, FakeProvider"}, provider)
        y = Yokel(config=config)

        # Act
        result = y.model("fake-model")

        # Assert
        assert isinstance(result, MessageBuilder), (
            "Expected model() to return a MessageBuilder"
        )

    def test_model_sets_model_id_on_builder(self) -> None:
        """model() passes model_id through to MessageBuilder._model."""
        # Arrange
        provider = FakeProvider()
        config = _make_config({"fake-*": "fake_module, FakeProvider"}, provider)
        y = Yokel(config=config)

        # Act
        result = y.model("fake-model-x")

        # Assert
        assert result._model == "fake-model-x", (
            "Expected MessageBuilder._model to equal the requested model_id"
        )

    def test_model_uses_provider_default_max_tokens_when_not_supplied(self) -> None:
        """model() reads provider.default_max_tokens when max_tokens is None."""
        # Arrange
        provider = FakeProvider()  # default_max_tokens = 512
        config = _make_config({"fake-*": "fake_module, FakeProvider"}, provider)
        y = Yokel(config=config)

        # Act
        result = y.model("fake-model")

        # Assert
        assert result._max_tokens == 512, (
            "Expected _max_tokens to equal provider.default_max_tokens (512)"
        )

    def test_model_with_explicit_max_tokens_overrides_provider_default(self) -> None:
        """model() uses the explicit max_tokens arg over provider.default_max_tokens."""
        # Arrange
        provider = FakeProvider()
        config = _make_config({"fake-*": "fake_module, FakeProvider"}, provider)
        y = Yokel(config=config)

        # Act
        result = y.model("fake-model", max_tokens=2048)

        # Assert
        assert result._max_tokens == 2048, (
            "Expected _max_tokens to equal the explicitly provided value (2048)"
        )

    def test_model_initialises_builder_with_no_system_or_messages(self) -> None:
        """model() creates a MessageBuilder with _system=None and _messages=()."""
        # Arrange
        provider = FakeProvider()
        config = _make_config({"fake-*": "fake_module, FakeProvider"}, provider)
        y = Yokel(config=config)

        # Act
        result = y.model("fake-model")

        # Assert
        assert result._system is None, (
            "Expected _system to be None on a freshly created builder"
        )
        assert result._messages == (), (
            "Expected _messages to be an empty tuple on a freshly created builder"
        )

    def test_model_with_no_matching_pattern_raises_unknown_model_error(self) -> None:
        """model() raises UnknownModelError when no provider pattern matches."""
        # Arrange
        config = _make_config({"claude-*": "some_module, SomeClass"}, None)
        y = Yokel(config=config)

        # Act & Assert
        with pytest.raises(UnknownModelError) as exc_info:
            y.model("gpt-4")

        assert exc_info.value.model_id == "gpt-4", (
            "Expected UnknownModelError.model_id to equal the unmatched model_id"
        )

    def test_model_propagates_auth_error_from_provider_construction(self) -> None:
        """model() propagates AuthError raised during provider construction."""
        # Arrange
        plugins_mock = MagicMock()
        plugins_mock.build.return_value = {"fake-*": "fake_module, FakeProvider"}
        plugins_mock.activate.side_effect = AuthError("Bad API key")
        config = MagicMock(spec=ConfigurationManager)
        config.plugins = plugins_mock
        config.value_store = MagicMock()
        y = Yokel(config=config)
        # Act & Assert
        with pytest.raises(AuthError, match="Bad API key"):
            y.model("fake-model")


class TestYokelResolveProvider:
    """Tests for Yokel._resolve_provider."""

    def test_resolve_provider_with_glob_pattern_returns_provider(self) -> None:
        """_resolve_provider returns the activated provider when a pattern matches."""
        # Arrange
        provider = FakeProvider()
        config = _make_config({"claude-*": "some_module, SomeClass"}, provider)
        y = Yokel(config=config)

        # Act
        result = y._resolve_provider("claude-opus-4-8")

        # Assert
        assert result is provider, (
            "Expected _resolve_provider to return the activated provider instance"
        )

    def test_resolve_provider_first_registered_pattern_wins(self) -> None:
        """_resolve_provider activates only the first matching pattern."""
        # Arrange
        first_provider = FakeProvider()
        plugins_mock = MagicMock()
        plugins_mock.build.return_value = {
            "claude-*": "module_a, ClassA",
            "claude-opus-*": "module_b, ClassB",
        }
        plugins_mock.activate.return_value = first_provider
        config = MagicMock(spec=ConfigurationManager)
        config.plugins = plugins_mock
        config.value_store = MagicMock()
        y = Yokel(config=config)
        # Act
        result = y._resolve_provider("claude-opus-4-8")

        # Assert
        assert result is first_provider, (
            "Expected the first registered matching pattern to win"
        )
        plugins_mock.activate.assert_called_once_with(
            "claude-*", value_store=config.value_store
        )

    def test_resolve_provider_passes_value_store_to_activate(self) -> None:
        """_resolve_provider passes value_store kwarg to activate."""
        # Arrange
        provider = FakeProvider()
        plugins_mock = MagicMock()
        plugins_mock.build.return_value = {"fake-*": "fake_module, FakeProvider"}
        plugins_mock.activate.return_value = provider
        value_store_mock = MagicMock()
        config = MagicMock(spec=ConfigurationManager)
        config.plugins = plugins_mock
        config.value_store = value_store_mock
        y = Yokel(config=config)
        # Act
        y._resolve_provider("fake-model")

        # Assert
        plugins_mock.activate.assert_called_once_with(
            "fake-*", value_store=value_store_mock
        )

    def test_resolve_provider_with_no_match_raises_unknown_model_error(self) -> None:
        """_resolve_provider raises UnknownModelError when no pattern matches."""
        # Arrange
        config = _make_config({"claude-*": "some_module, SomeClass"}, None)
        y = Yokel(config=config)

        # Act & Assert
        with pytest.raises(UnknownModelError) as exc_info:
            y._resolve_provider("gpt-4-turbo")

        assert exc_info.value.model_id == "gpt-4-turbo", (
            "Expected UnknownModelError.model_id to match the unresolved model_id"
        )

    def test_resolve_provider_propagates_auth_error(self) -> None:
        """_resolve_provider propagates AuthError raised by provider construction."""
        # Arrange
        plugins_mock = MagicMock()
        plugins_mock.build.return_value = {"fake-*": "fake_module, FakeProvider"}
        plugins_mock.activate.side_effect = AuthError("Missing credentials")
        config = MagicMock(spec=ConfigurationManager)
        config.plugins = plugins_mock
        config.value_store = MagicMock()
        y = Yokel(config=config)
        # Act & Assert
        with pytest.raises(AuthError, match="Missing credentials"):
            y._resolve_provider("fake-model")
