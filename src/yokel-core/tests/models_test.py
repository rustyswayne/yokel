"""Tests for core.models: Tool.from_dict, Response construction."""

from __future__ import annotations

from yokel.core.models import Response, Tool, Usage


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
