"""Tests for _yokel.Yokel: singleton lifecycle, conf, model, _resolve_provider."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from yokel._builder import MessageBuilder
from yokel._registry import register_provider, register_tool
from yokel._yokel import Yokel
from yokel.core.configuration.manager import ConfigurationManager
from yokel.core.errors import AuthError, UnknownModelError
from yokel.core.models import Response, Tool
from yokel.providers import ProviderInterface


class FakeProvider(ProviderInterface):
    """Minimal ProviderInterface stub for testing; raises NotImplementedError."""

    default_max_tokens: int = 512

    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
        *,
        tools: tuple[Any, ...] = (),
        tool_choice: Any = None,
    ) -> Response:
        raise NotImplementedError

    def encode_assistant_turn(self, response: Response) -> dict[str, Any]:
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


def _make_yokel_with_config(patterns: dict[str, str], provider: Any) -> Yokel:
    """Return an isolated Yokel whose _config resolves patterns to provider."""
    y = Yokel(config={})
    y._config = _make_config(patterns, provider)
    return y


class TestYokelSingleton:
    """Tests for Yokel's process-level singleton lifecycle."""

    def test_bare_construction_returns_same_instance(self) -> None:
        """Yokel() returns the same instance on every call."""
        # Arrange & Act
        first = Yokel()
        second = Yokel()

        # Assert
        assert first is second, "Expected repeated Yokel() calls to share an instance"

    def test_explicit_config_returns_independent_instance(self) -> None:
        """Yokel(config=...) returns an instance distinct from the singleton."""
        # Arrange
        singleton = Yokel()

        # Act
        isolated = Yokel(config={})

        # Assert
        assert isolated is not singleton, (
            "Expected Yokel(config=...) to bypass the shared singleton"
        )

    def test_explicit_config_instances_are_each_independent(self) -> None:
        """Two Yokel(config=...) calls return two distinct instances."""
        # Act
        first = Yokel(config={})
        second = Yokel(config={})

        # Assert
        assert first is not second, (
            "Expected each Yokel(config=...) call to return a fresh instance"
        )

    def test_repeated_bare_construction_preserves_singleton_state(self) -> None:
        """Mutations on the singleton's manager persist across Yokel() calls."""
        # Arrange
        first = Yokel()
        first.conf.value_store.upsert("marker", "set")

        # Act
        second = Yokel()

        # Assert
        assert second.conf.value_store.get("marker") == "set", (
            "Expected singleton state to persist across repeated Yokel() calls"
        )


class TestYokelInit:
    """Tests for Yokel.__init__."""

    def test_init_without_config_creates_configuration_manager(self) -> None:
        """Yokel() owns a ConfigurationManager."""
        # Arrange & Act
        y = Yokel()

        # Assert
        assert isinstance(y.conf, ConfigurationManager), (
            "Expected a ConfigurationManager when no config is provided"
        )

    def test_init_with_config_patches_value_store(self) -> None:
        """Yokel(config={...}) writes the dict into the instance's value_store."""
        # Act
        y = Yokel(config={"anthropic_api_key": "sk-test"})

        # Assert
        assert y.conf.value_store.get("anthropic_api_key") == "sk-test", (
            "Expected the config dict to be applied to value_store"
        )

    def test_init_merges_default_config_under_explicit_config(self) -> None:
        """Explicit config values take precedence over DEFAULT_CONFIG."""
        # Arrange
        original_default_config = Yokel.DEFAULT_CONFIG
        Yokel.DEFAULT_CONFIG = {"a": "from-default", "b": "from-default"}

        try:
            # Act
            y = Yokel(config={"a": "from-explicit"})

            # Assert
            assert y.conf.value_store.get("a") == "from-explicit", (
                "Expected explicit config to override DEFAULT_CONFIG"
            )
            assert y.conf.value_store.get("b") == "from-default", (
                "Expected DEFAULT_CONFIG values to survive when not overridden"
            )
        finally:
            Yokel.DEFAULT_CONFIG = original_default_config

    def test_init_strips_plugins_key_from_config_before_patching_value_store(
        self,
    ) -> None:
        """A "plugins" key in config is not written into value_store."""
        # Act
        y = Yokel(config={"plugins": {"claude-*": "module, Class"}, "other": "value"})

        # Assert
        assert y.conf.value_store.get("plugins") is None, (
            "Expected 'plugins' to be stripped before patching value_store"
        )
        assert y.conf.value_store.get("other") == "value"

    def test_init_seeds_plugins_section_from_default_registry(self) -> None:
        """Yokel() seeds its plugins section from the default provider registry."""
        # Arrange
        register_provider("claude-*", "yokel_anthropic, AnthropicProvider")

        # Act
        y = Yokel(config={})

        # Assert
        assert y.conf.plugins.get("claude-*") == "yokel_anthropic, AnthropicProvider", (
            "Expected the default registry pattern to seed the plugins section"
        )

    def test_init_does_not_seed_plugins_registered_with_default_false(self) -> None:
        """Patterns registered with default=False are not seeded into plugins."""
        # Arrange
        register_provider(
            "claude-*", "yokel_anthropic, AnthropicProvider", default=False
        )

        # Act
        y = Yokel(config={})

        # Assert
        assert y.conf.plugins.get("claude-*") is None, (
            "Expected default=False registrations to be excluded from seeding"
        )


class TestYokelToolRegistration:
    """Tests for Yokel(tools=...), register_tools, and tools section seeding."""

    def test_init_seeds_tools_section_from_default_registry(self) -> None:
        """Yokel() seeds its tools section from the default tool registry."""
        # Arrange
        tool = Tool(name="get_weather", description="d", input_schema={})
        register_tool(tool)

        # Act
        y = Yokel(config={})

        # Assert
        assert y.conf.tools.get("get_weather") is tool, (
            "Expected the default tool registry to seed the tools section"
        )

    def test_init_does_not_seed_tools_registered_with_default_false(self) -> None:
        """Tools registered with default=False are not seeded into tools."""
        # Arrange
        tool = Tool(name="get_weather", description="d", input_schema={})
        register_tool(tool, default=False)

        # Act
        y = Yokel(config={})

        # Assert
        assert y.conf.tools.get("get_weather") is None, (
            "Expected default=False registrations to be excluded from seeding"
        )

    def test_constructor_tools_are_resolvable_on_that_instance(self) -> None:
        """Yokel(tools=[...]) makes each tool resolvable via conf.tools.get."""
        # Arrange
        tool = Tool(name="search", description="d", input_schema={})

        # Act
        y = Yokel(config={}, tools=[tool])

        # Assert
        assert y.conf.tools.get("search") is tool, (
            "Expected a constructor-supplied tool to be resolvable on this instance"
        )

    def test_constructor_tools_layer_on_top_of_default_registry(self) -> None:
        """Constructor tools= does not replace tools seeded from the default registry"""
        # Arrange
        default_tool = Tool(name="get_weather", description="d", input_schema={})
        register_tool(default_tool)
        extra_tool = Tool(name="search", description="d", input_schema={})

        # Act
        y = Yokel(config={}, tools=[extra_tool])

        # Assert
        assert y.conf.tools.get("get_weather") is default_tool, (
            "Expected the default registry's tool to still be present"
        )
        assert y.conf.tools.get("search") is extra_tool, (
            "Expected the constructor-supplied tool to also be present"
        )

    def test_register_tools_adds_tool_after_construction(self) -> None:
        """register_tools() called after construction makes the tool resolvable."""
        # Arrange
        y = Yokel(config={})
        tool = Tool(name="search", description="d", input_schema={})

        # Act
        y.register_tools(tool)

        # Assert
        assert y.conf.tools.get("search") is tool, (
            "Expected register_tools() to register the tool on this instance"
        )

    def test_register_tools_accepts_multiple_tools(self) -> None:
        """register_tools() registers every tool passed in a single call."""
        # Arrange
        y = Yokel(config={})
        weather = Tool(name="get_weather", description="d", input_schema={})
        search = Tool(name="search", description="d", input_schema={})

        # Act
        y.register_tools(weather, search)

        # Assert
        assert y.conf.tools.get("get_weather") is weather
        assert y.conf.tools.get("search") is search

    def test_register_tools_on_singleton_via_constructor_call(self) -> None:
        """Yokel(tools=[...]) with no config registers onto the existing singleton."""
        # Arrange
        singleton = Yokel()
        tool = Tool(name="search", description="d", input_schema={})

        # Act
        again = Yokel(tools=[tool])

        # Assert
        assert again is singleton, (
            "Expected Yokel(tools=...) with no config to return the singleton"
        )
        assert singleton.conf.tools.get("search") is tool, (
            "Expected the tool to be registered onto the existing singleton"
        )

    def test_model_builder_tool_resolver_resolves_registered_tool(self) -> None:
        """The MessageBuilder from model() resolves names via this instance's tools."""
        # Arrange
        provider = FakeProvider()
        tool = Tool(name="search", description="d", input_schema={})
        y = Yokel(config={})
        y._resolve_provider = lambda model_id: provider  # type: ignore[method-assign]
        y.register_tools(tool)

        # Act
        builder = y.model("fake-model")

        # Assert
        assert builder._tool_resolver("search") is tool, (
            "Expected the builder's _tool_resolver to resolve a registered tool"
        )


class TestYokelConf:
    """Tests for Yokel.conf."""

    def test_conf_returns_owned_configuration_manager(self) -> None:
        """conf exposes the ConfigurationManager owned by this instance."""
        # Arrange
        y = Yokel(config={})

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
        y = _make_yokel_with_config({"fake-*": "fake_module, FakeProvider"}, provider)

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
        y = _make_yokel_with_config({"fake-*": "fake_module, FakeProvider"}, provider)

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
        y = _make_yokel_with_config({"fake-*": "fake_module, FakeProvider"}, provider)

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
        y = _make_yokel_with_config({"fake-*": "fake_module, FakeProvider"}, provider)

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
        y = _make_yokel_with_config({"fake-*": "fake_module, FakeProvider"}, provider)

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
        y = _make_yokel_with_config({"claude-*": "some_module, SomeClass"}, None)

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
        y = Yokel(config={})
        y._config = config

        # Act & Assert
        with pytest.raises(AuthError, match="Bad API key"):
            y.model("fake-model")


class TestYokelResolveProvider:
    """Tests for Yokel._resolve_provider."""

    def test_resolve_provider_with_glob_pattern_returns_provider(self) -> None:
        """_resolve_provider returns the activated provider when a pattern matches."""
        # Arrange
        provider = FakeProvider()
        y = _make_yokel_with_config({"claude-*": "some_module, SomeClass"}, provider)

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
        y = Yokel(config={})
        y._config = config

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
        y = Yokel(config={})
        y._config = config

        # Act
        y._resolve_provider("fake-model")

        # Assert
        plugins_mock.activate.assert_called_once_with(
            "fake-*", value_store=value_store_mock
        )

    def test_resolve_provider_with_no_match_raises_unknown_model_error(self) -> None:
        """_resolve_provider raises UnknownModelError when no pattern matches."""
        # Arrange
        y = _make_yokel_with_config({"claude-*": "some_module, SomeClass"}, None)

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
        y = Yokel(config={})
        y._config = config

        # Act & Assert
        with pytest.raises(AuthError, match="Missing credentials"):
            y._resolve_provider("fake-model")
