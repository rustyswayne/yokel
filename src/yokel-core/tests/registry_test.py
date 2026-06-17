"""Tests for _registry.register_provider and get_default_providers."""

from __future__ import annotations

from yokel._registry import get_default_providers, register_provider


class TestRegisterProvider:
    """Tests for register_provider."""

    def test_register_provider_adds_pattern_to_default_registry(self) -> None:
        """register_provider() with default=True adds the pattern/target pair."""
        # Act
        register_provider("claude-*", "yokel_anthropic, AnthropicProvider")

        # Assert
        assert get_default_providers() == {
            "claude-*": "yokel_anthropic, AnthropicProvider"
        }

    def test_register_provider_defaults_to_default_true(self) -> None:
        """register_provider() without an explicit default kwarg registers it."""
        # Act
        register_provider("gpt-*", "yokel_openai, OpenAiProvider")

        # Assert
        assert get_default_providers() == {"gpt-*": "yokel_openai, OpenAiProvider"}

    def test_register_provider_with_default_false_is_a_noop(self) -> None:
        """register_provider(default=False) does not add the pattern."""
        # Act
        register_provider(
            "claude-*", "yokel_anthropic, AnthropicProvider", default=False
        )

        # Assert
        assert get_default_providers() == {}

    def test_register_provider_overwrites_existing_pattern(self) -> None:
        """Re-registering a pattern overwrites its previous target."""
        # Arrange
        register_provider("claude-*", "module_a, ClassA")

        # Act
        register_provider("claude-*", "module_b, ClassB")

        # Assert
        assert get_default_providers() == {"claude-*": "module_b, ClassB"}

    def test_register_provider_keeps_multiple_distinct_patterns(self) -> None:
        """Registering distinct patterns keeps all of them."""
        # Act
        register_provider("claude-*", "yokel_anthropic, AnthropicProvider")
        register_provider("gpt-*", "yokel_openai, OpenAiProvider")

        # Assert
        assert get_default_providers() == {
            "claude-*": "yokel_anthropic, AnthropicProvider",
            "gpt-*": "yokel_openai, OpenAiProvider",
        }


class TestGetDefaultProviders:
    """Tests for get_default_providers."""

    def test_get_default_providers_returns_empty_dict_when_unregistered(self) -> None:
        """get_default_providers() returns {} when nothing was registered."""
        # Act
        result = get_default_providers()

        # Assert
        assert result == {}

    def test_get_default_providers_returns_a_copy(self) -> None:
        """Mutating the returned dict does not affect the underlying registry."""
        # Arrange
        register_provider("claude-*", "yokel_anthropic, AnthropicProvider")

        # Act
        result = get_default_providers()
        result["claude-*"] = "tampered, Tampered"

        # Assert
        assert get_default_providers() == {
            "claude-*": "yokel_anthropic, AnthropicProvider"
        }
