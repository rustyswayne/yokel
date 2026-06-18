"""Tests for _registry.register_provider, get_default_providers, register_tool,
and get_default_tools."""

from __future__ import annotations

from yokel._registry import (
    get_default_providers,
    get_default_tools,
    register_provider,
    register_tool,
)
from yokel.core.models import Tool


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


class TestRegisterTool:
    """Tests for register_tool."""

    def test_register_tool_adds_tool_keyed_by_name(self) -> None:
        """register_tool() with default=True adds the tool keyed by its name."""
        # Arrange
        tool = Tool(name="get_weather", description="Look up weather.", input_schema={})

        # Act
        register_tool(tool)

        # Assert
        assert get_default_tools() == {"get_weather": tool}

    def test_register_tool_defaults_to_default_true(self) -> None:
        """register_tool() without an explicit default kwarg registers it."""
        # Arrange
        tool = Tool(name="search", description="Search the web.", input_schema={})

        # Act
        register_tool(tool)

        # Assert
        assert get_default_tools() == {"search": tool}

    def test_register_tool_with_default_false_is_a_noop(self) -> None:
        """register_tool(default=False) does not add the tool."""
        # Arrange
        tool = Tool(name="get_weather", description="Look up weather.", input_schema={})

        # Act
        register_tool(tool, default=False)

        # Assert
        assert get_default_tools() == {}

    def test_register_tool_overwrites_existing_name(self) -> None:
        """Re-registering the same name overwrites its previous registration."""
        # Arrange
        tool_a = Tool(name="get_weather", description="Version A.", input_schema={})
        tool_b = Tool(name="get_weather", description="Version B.", input_schema={})
        register_tool(tool_a)

        # Act
        register_tool(tool_b)

        # Assert
        assert get_default_tools() == {"get_weather": tool_b}

    def test_register_tool_keeps_multiple_distinct_names(self) -> None:
        """Registering distinct tool names keeps all of them."""
        # Arrange
        weather = Tool(
            name="get_weather", description="Look up weather.", input_schema={}
        )
        search = Tool(name="search", description="Search the web.", input_schema={})

        # Act
        register_tool(weather)
        register_tool(search)

        # Assert
        assert get_default_tools() == {"get_weather": weather, "search": search}


class TestGetDefaultTools:
    """Tests for get_default_tools."""

    def test_get_default_tools_returns_empty_dict_when_unregistered(self) -> None:
        """get_default_tools() returns {} when nothing was registered."""
        # Act
        result = get_default_tools()

        # Assert
        assert result == {}

    def test_get_default_tools_returns_a_copy(self) -> None:
        """Mutating the returned dict does not affect the underlying registry."""
        # Arrange
        tool = Tool(name="get_weather", description="Look up weather.", input_schema={})
        register_tool(tool)

        # Act
        result = get_default_tools()
        result["get_weather"] = Tool(name="tampered", description="x", input_schema={})

        # Assert
        assert get_default_tools() == {"get_weather": tool}
