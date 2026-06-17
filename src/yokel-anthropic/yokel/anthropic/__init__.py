"""Public API for yokel.anthropic.

    import yokel.anthropic
    from yokel.api import Yokel
    y = Yokel()
    response = y.model("claude-opus-4-8").user("Hello").send()

Importing this module registers the "claude-*" pattern in yokel's
process-level default provider registry, so a subsequently constructed
Yokel() resolves claude-* with no explicit wiring. Use register() instead
for isolated/test construction that bypasses the default registry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from yokel._registry import register_provider
from yokel.anthropic._provider import AnthropicProvider as AnthropicProvider

if TYPE_CHECKING:
    from yokel._yokel import Yokel
    from yokel.core.configuration.interfaces import IConfigurationManager

__all__ = ["AnthropicProvider", "register"]

_TARGET = "yokel.anthropic, AnthropicProvider"


def register(target: Yokel | IConfigurationManager) -> None:
    """Register "claude-*" directly on a manager, bypassing the default registry.

    Args:
        target: A Yokel instance (its `.conf` is used) or a
            ConfigurationManager to register against directly -- no
            process-level/global state is touched.
    """
    manager = target.conf if hasattr(target, "conf") else target
    manager.plugins.upsert("claude-*", _TARGET)


register_provider("claude-*", _TARGET, default=True)
