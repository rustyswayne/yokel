"""Tests for core.errors: UnknownToolError, NoToolHandlerError, ToolLoopLimitError."""

from __future__ import annotations

from yokel.core.errors import (
    NoToolHandlerError,
    ToolLoopLimitError,
    UnknownToolError,
    YokelError,
)


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


class TestNoToolHandlerError:
    """Tests for NoToolHandlerError."""

    def test_no_tool_handler_error_is_a_yokel_error(self) -> None:
        """NoToolHandlerError subclasses YokelError."""
        # Act
        result = NoToolHandlerError("get_weather")

        # Assert
        assert isinstance(result, YokelError), (
            "Expected NoToolHandlerError to be a YokelError"
        )

    def test_no_tool_handler_error_stores_name(self) -> None:
        """NoToolHandlerError.name equals the unresolved name."""
        # Act
        result = NoToolHandlerError("get_weather")

        # Assert
        assert result.name == "get_weather", (
            "Expected name to equal the unresolved tool call name"
        )

    def test_no_tool_handler_error_message_mentions_name(self) -> None:
        """NoToolHandlerError's message includes the unresolved name."""
        # Act
        result = NoToolHandlerError("get_weather")

        # Assert
        assert "get_weather" in str(result), (
            "Expected the error message to mention the unresolved name"
        )


class TestToolLoopLimitError:
    """Tests for ToolLoopLimitError."""

    def test_tool_loop_limit_error_is_a_yokel_error(self) -> None:
        """ToolLoopLimitError subclasses YokelError."""
        # Act
        result = ToolLoopLimitError(10)

        # Assert
        assert isinstance(result, YokelError), (
            "Expected ToolLoopLimitError to be a YokelError"
        )

    def test_tool_loop_limit_error_stores_max_iterations(self) -> None:
        """ToolLoopLimitError.max_iterations equals the limit that was hit."""
        # Act
        result = ToolLoopLimitError(10)

        # Assert
        assert result.max_iterations == 10, (
            "Expected max_iterations to equal the limit that was hit"
        )

    def test_tool_loop_limit_error_message_mentions_max_iterations(self) -> None:
        """ToolLoopLimitError's message includes the iteration limit."""
        # Act
        result = ToolLoopLimitError(10)

        # Assert
        assert "10" in str(result), (
            "Expected the error message to mention the iteration limit"
        )
