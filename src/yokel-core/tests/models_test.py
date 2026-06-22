"""Tests for core.models: Tool.from_dict, Response construction, ToolChoice."""

from __future__ import annotations

import pytest
from yokel.core.models import Response, Tool, ToolChoice, Usage


class TestToolFromDict:
    """Tests for Tool.from_dict."""

    def test_from_dict_with_valid_dict_returns_tool(self) -> None:
        """from_dict() builds a Tool matching the dict's fields."""
        # Arrange
        d = {
            "name": "get_weather",
            "description": "Look up the current weather for a city.",
            "input_schema": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        }

        # Act
        result = Tool.from_dict(d)

        # Assert
        assert result == Tool(
            name="get_weather",
            description="Look up the current weather for a city.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        ), "Expected Tool fields to match the source dict"


class TestResponse:
    """Tests for Response construction with the new tool_calls/raw_content fields."""

    def test_response_without_tool_calls_defaults_to_empty_tuple(self) -> None:
        """Response() omitting tool_calls defaults to an empty tuple."""
        # Act
        result = Response(
            text="hi", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )

        # Assert
        assert result.tool_calls == (), "Expected tool_calls to default to ()"

    def test_response_without_raw_content_defaults_to_none(self) -> None:
        """Response() omitting raw_content defaults to None."""
        # Act
        result = Response(
            text="hi", model="m", stop_reason="end_turn", usage=Usage(0, 0)
        )

        # Assert
        assert result.raw_content is None, "Expected raw_content to default to None"


class TestToolChoiceConstructors:
    """Tests for ToolChoice's classmethod constructors."""

    def test_auto_sets_mode_auto_and_no_name(self) -> None:
        """auto() returns a ToolChoice with mode='auto' and name=None."""
        # Act
        result = ToolChoice.auto()

        # Assert
        assert result == ToolChoice(mode="auto"), "Expected mode='auto', name=None"

    def test_required_sets_mode_required_and_no_name(self) -> None:
        """required() returns a ToolChoice with mode='required' and name=None."""
        # Act
        result = ToolChoice.required()

        # Assert
        assert result == ToolChoice(mode="required"), (
            "Expected mode='required', name=None"
        )

    def test_none_sets_mode_none_and_no_name(self) -> None:
        """none() returns a ToolChoice with mode='none' and name=None."""
        # Act
        result = ToolChoice.none()

        # Assert
        assert result == ToolChoice(mode="none"), "Expected mode='none', name=None"

    def test_tool_sets_mode_tool_and_name(self) -> None:
        """tool(name) returns a ToolChoice with mode='tool' and the given name."""
        # Act
        result = ToolChoice.tool("get_weather")

        # Assert
        assert result == ToolChoice(mode="tool", name="get_weather"), (
            "Expected mode='tool', name='get_weather'"
        )


class TestToolChoiceValidationAtConstruction:
    """Tests for ToolChoice.__post_init__ validation."""

    def test_tool_mode_without_name_raises_value_error(self) -> None:
        """mode='tool' with no name raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="requires a non-empty name"):
            ToolChoice(mode="tool")

    def test_tool_mode_with_empty_name_raises_value_error(self) -> None:
        """mode='tool' with an empty-string name raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="requires a non-empty name"):
            ToolChoice(mode="tool", name="")

    def test_non_tool_mode_with_name_raises_value_error(self) -> None:
        """A non-'tool' mode with a name set raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="must not set name"):
            ToolChoice(mode="auto", name="get_weather")


class TestToolChoiceFromDict:
    """Tests for ToolChoice.from_dict."""

    def test_from_dict_with_tool_mode_round_trips_name(self) -> None:
        """from_dict() round-trips mode='tool' with its name."""
        # Act
        result = ToolChoice.from_dict({"mode": "tool", "name": "get_weather"})

        # Assert
        assert result == ToolChoice(mode="tool", name="get_weather"), (
            "Expected mode/name to round-trip from the dict"
        )

    def test_from_dict_without_name_key_defaults_to_none(self) -> None:
        """from_dict() omitting the name key defaults name to None."""
        # Act
        result = ToolChoice.from_dict({"mode": "auto"})

        # Assert
        assert result == ToolChoice(mode="auto"), "Expected name to default to None"

    def test_from_dict_applies_construction_validation(self) -> None:
        """from_dict() raises ValueError for an invalid mode/name pairing."""
        # Act & Assert
        with pytest.raises(ValueError, match="requires a non-empty name"):
            ToolChoice.from_dict({"mode": "tool"})


class TestToolChoiceValidateAgainst:
    """Tests for ToolChoice.validate_against."""

    def test_auto_with_no_tools_does_not_raise(self) -> None:
        """mode='auto' is always valid, even with no tools resolved."""
        # Act & Assert
        ToolChoice.auto().validate_against(())

    def test_none_with_no_tools_does_not_raise(self) -> None:
        """mode='none' is always valid, even with no tools resolved."""
        # Act & Assert
        ToolChoice.none().validate_against(())

    def test_required_with_no_tools_raises_value_error(self) -> None:
        """mode='required' with no resolved tools raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="requires at least one tool"):
            ToolChoice.required().validate_against(())

    def test_required_with_tools_does_not_raise(self) -> None:
        """mode='required' with at least one resolved tool is valid."""
        # Arrange
        tool = Tool(name="get_weather", description="d", input_schema={})

        # Act & Assert
        ToolChoice.required().validate_against((tool,))

    def test_tool_with_no_tools_raises_value_error(self) -> None:
        """mode='tool' with no resolved tools raises ValueError."""
        # Act & Assert
        with pytest.raises(ValueError, match="requires at least one tool"):
            ToolChoice.tool("get_weather").validate_against(())

    def test_tool_with_mismatched_name_raises_value_error(self) -> None:
        """mode='tool' naming a tool absent from the resolved set raises."""
        # Arrange
        tool = Tool(name="search", description="d", input_schema={})

        # Act & Assert
        with pytest.raises(ValueError, match="not in the resolved tool set"):
            ToolChoice.tool("get_weather").validate_against((tool,))

    def test_tool_with_matching_name_does_not_raise(self) -> None:
        """mode='tool' naming a tool present in the resolved set is valid."""
        # Arrange
        tool = Tool(name="get_weather", description="d", input_schema={})

        # Act & Assert
        ToolChoice.tool("get_weather").validate_against((tool,))
