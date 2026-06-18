from __future__ import annotations

import abc
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from yokel.core.models import Response


class ProviderInterface(metaclass=abc.ABCMeta):
    """Abstract base class for LLM provider adapters."""

    default_max_tokens: int = 1024

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if hasattr(subclass, "send") and callable(subclass.send):
            return True

        return cast(bool, NotImplemented)

    @abstractmethod
    def send(
        self,
        messages: tuple[dict[str, Any], ...],
        model: str,
        system: str | None,
        max_tokens: int,
    ) -> Response:
        """Send a chat request to the provider and return a normalised response.

        Args:
            messages: Ordered conversation turns as raw dicts (role + content).
            model: The model identifier to target (e.g. ``"claude-sonnet-4-6"``).
            system: Optional system prompt; pass ``None`` to omit.
            max_tokens: Upper bound on tokens the provider may generate.

        Returns:
            A normalised Response containing the generated text, model id,
            stop reason, and token usage.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError
