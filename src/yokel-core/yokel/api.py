"""Public API surface for yokel-core.

Relocated out of yokel/__init__.py (ADR-012): yokel/ is a PEP 420 namespace
package and cannot own an __init__.py. Import from here, not from the
internal modules directly:

    from yokel.api import Yokel
"""

from __future__ import annotations

from yokel._builder import MessageBuilder as MessageBuilder
from yokel._conversation import Conversation as Conversation
from yokel._registry import register_provider as register_provider
from yokel._yokel import Yokel as Yokel
from yokel.core.errors import (
    AuthError as AuthError,
    ProviderError as ProviderError,
    UnknownModelError as UnknownModelError,
    UnknownToolError as UnknownToolError,
    YokelError as YokelError,
)
from yokel.core.models import (
    Response as Response,
    Tool as Tool,
    ToolCall as ToolCall,
    ToolChoice as ToolChoice,
    Usage as Usage,
)
from yokel.providers import ProviderInterface as ProviderInterface

__all__ = [
    "Yokel",
    "MessageBuilder",
    "Conversation",
    "register_provider",
    "Response",
    "Tool",
    "ToolCall",
    "ToolChoice",
    "Usage",
    "ProviderInterface",
    "YokelError",
    "AuthError",
    "ProviderError",
    "UnknownModelError",
    "UnknownToolError",
]
