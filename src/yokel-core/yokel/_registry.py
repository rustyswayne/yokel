from __future__ import annotations

_default_registry: dict[str, str] = {}


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
