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
            "Install and import the appropriate yokel provider package before calling model()."
        )
        self.model_id = model_id
