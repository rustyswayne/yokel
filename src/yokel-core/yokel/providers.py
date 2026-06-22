from __future__ import annotations

import abc
from abc import abstractmethod
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from yokel.core.models import Response, Tool, ToolChoice


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
        *,
        tools: tuple[Tool, ...] = (),
        tool_choice: ToolChoice | None = None,
    ) -> Response:
        """Send a chat request to the provider and return a normalised response.

        Args:
            messages: Ordered conversation turns as raw dicts (role + content).
            model: The model identifier to target (e.g. ``"claude-sonnet-4-6"``).
            system: Optional system prompt; pass ``None`` to omit.
            max_tokens: Upper bound on tokens the provider may generate.
            tools: Already-resolved tool declarations to offer the model.
                Resolution from name to Tool happens in yokel-core before
                this call; implementations never look up tools by name
                themselves. Omit the provider's native tools parameter
                entirely when this is empty.
            tool_choice: Optional normalized control over whether/which tool
                the model must use. ``None`` means omit the provider's native
                tool_choice parameter entirely.

        Returns:
            A normalised Response containing the generated text, model id,
            stop reason, token usage, any requested tool calls, and the
            provider's native response content.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError

    @abstractmethod
    def encode_assistant_turn(self, response: Response) -> dict[str, Any]:
        """Re-encode a Response as a provider-native assistant history turn.

        Reconstructs the assistant message content (text and/or tool_use
        blocks) from ``response.text``/``response.tool_calls`` so it can be
        replayed verbatim, id-for-id, on the next request. Returns the
        provider-native ``content`` value only -- the caller (Conversation)
        wraps it with the yokel-level ``kind`` discriminator before
        appending it to history.

        Args:
            response: The Response whose assistant turn is being replayed.

        Returns:
            A dict suitable as the ``content`` of a replayed assistant
            message in this provider's native shape.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError
