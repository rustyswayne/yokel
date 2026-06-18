from __future__ import annotations

from yokel.core.models import Tool

_default_registry: dict[str, str] = {}
_default_tool_registry: dict[str, Tool] = {}


def register_provider(pattern: str, target: str, *, default: bool = True) -> None:
    """Register a provider pattern in the process-level default registry.

    Provider packages call this at import time so a subsequently constructed
    Yokel() resolves pattern without any explicit wiring call. The registry
    holds pattern-only discovery metadata ("module, class" strings) -- API
    keys and other secrets never pass through it.

    Args:
        pattern: A glob-style model ID pattern (e.g. "claude-*").
        target: The provider's "module_name, class_name" string.
        default: When False, this call is a no-op and target is not added to
            the default registry -- used by callers that want to register a
            provider class without opting it into the import-and-go default
            wiring.
    """
    if not default:
        return

    _default_registry[pattern] = target


def get_default_providers() -> dict[str, str]:
    """Return a copy of the process-level default provider registry."""
    return dict(_default_registry)


def register_tool(tool: Tool, *, default: bool = True) -> None:
    """Register a Tool in the process-level default tool registry.

    Tool packages or application startup code call this at import time, or
    explicitly, so a subsequently constructed Yokel() resolves the tool by
    name without any explicit wiring call. Keyed by tool.name -- a
    re-registration with the same name overwrites the previous one
    (matches register_provider's last-write-wins semantics).

    Args:
        tool: The Tool to register.
        default: When False, this call is a no-op and tool is not added to
            the default registry -- used by callers that want to construct
            a Tool without opting it into the import-and-go default wiring.
    """
    if not default:
        return

    _default_tool_registry[tool.name] = tool


def get_default_tools() -> dict[str, Tool]:
    """Return a copy of the process-level default tool registry."""
    return dict(_default_tool_registry)
