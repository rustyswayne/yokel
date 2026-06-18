"""Tests for core.errors: UnknownToolError."""

from __future__ import annotations

from yokel.core.errors import UnknownToolError, YokelError


class TestUnknownToolError:
    """Tests for UnknownToolError."""

    def test_unknown_tool_error_is_a_yokel_error(self) -> None:
        """UnknownToolError subclasses YokelError."""
        # Act
        result = UnknownToolError("get_weather")

        # Assert
        assert isinstance(result, YokelError), (
            "Expected UnknownToolError to be a YokelError"
        )

    def test_unknown_tool_error_stores_tool_name(self) -> None:
        """UnknownToolError.tool_name equals the unresolved name."""
        # Act
        result = UnknownToolError("get_weather")

        # Assert
        assert result.tool_name == "get_weather", (
            "Expected tool_name to equal the unresolved tool name"
        )

    def test_unknown_tool_error_message_mentions_tool_name(self) -> None:
        """UnknownToolError's message includes the unresolved name."""
        # Act
        result = UnknownToolError("get_weather")

        # Assert
        assert "get_weather" in str(result), (
            "Expected the error message to mention the unresolved tool name"
        )
