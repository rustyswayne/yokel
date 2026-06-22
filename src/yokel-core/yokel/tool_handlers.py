from __future__ import annotations

import abc
from abc import abstractmethod
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from yokel.core.models import ToolCall, ToolResult


class ToolHandlerInterface(metaclass=abc.ABCMeta):
    """Abstract base class for tool-call handlers run by the core executor."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if hasattr(subclass, "handle") and callable(subclass.handle):
            return True

        return cast(bool, NotImplemented)

    @abstractmethod
    def handle(self, call: ToolCall) -> ToolResult:
        """Run the tool the model requested and return its result.

        Args:
            call: The tool-use request the model issued.

        Returns:
            A ToolResult to feed back to the model.

        Raises:
            NotImplementedError: Subclasses must override this method.
        """
        raise NotImplementedError
