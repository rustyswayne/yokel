from __future__ import annotations


class YokelError(Exception):
    """Base class for all yokel errors."""


class AuthError(YokelError):
    """Raised when provider authentication fails or a credential is missing."""


class ProviderError(YokelError):
    """Raised when the upstream provider returns an HTTP or API-level error.

    Attributes:
        status_code: The HTTP status code returned by the provider.
        provider_message: The raw error message from the provider.
    """

    def __init__(
        self, message: str, *, status_code: int, provider_message: str
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider_message = provider_message


class UnknownModelError(YokelError):
    """Raised when no installed provider claims the requested model ID.

    Attributes:
        model_id: The model identifier that could not be resolved.
    """

    def __init__(self, model_id: str) -> None:
        super().__init__(
            f"No provider is registered for model '{model_id}'. "
            "Install and import the appropriate yokel provider package "
            "before calling model()."
        )
        self.model_id = model_id


class UnknownToolError(YokelError):
    """Raised when no registered tool matches a name passed to .tools().

    Attributes:
        tool_name: The tool name that could not be resolved.
    """

    def __init__(self, tool_name: str) -> None:
        super().__init__(
            f"No tool is registered for name '{tool_name}'. "
            "Register the tool with register_tool() or Yokel(tools=[...]) "
            "before calling tools()."
        )
        self.tool_name = tool_name


class NoToolHandlerError(YokelError):
    """Raised when no registered handler resolves for a requested tool call.

    Attributes:
        name: The tool call name that could not be resolved to a handler.
    """

    def __init__(self, name: str) -> None:
        super().__init__(
            f"No tool handler is registered for name '{name}'. "
            "Register the handler with register_tool_handler() or "
            "Yokel(tool_handlers={...}) before calling run_tools()."
        )
        self.name = name


class ToolLoopLimitError(YokelError):
    """Raised when run_tools() exceeds its maximum number of iterations.

    Attributes:
        max_iterations: The iteration limit that was hit.
    """

    def __init__(self, max_iterations: int) -> None:
        super().__init__(
            f"run_tools() exceeded the maximum of {max_iterations} "
            "iteration(s) without the model stopping its tool requests."
        )
        self.max_iterations = max_iterations
