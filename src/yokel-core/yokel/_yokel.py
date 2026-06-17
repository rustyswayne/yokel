from __future__ import annotations

import fnmatch
from typing import Any, ClassVar, cast

from yokel._builder import MessageBuilder
from yokel._registry import get_default_providers
from yokel.core.configuration.manager import ConfigurationManager
from yokel.core.errors import UnknownModelError
from yokel.providers import Provider


class Yokel:
    """Primary entry point for the yokel library.

    Yokel() is a process-level singleton: every call with no config argument
    returns the same instance. Its ConfigurationManager seeds the "plugins"
    section from the process-level default provider registry, so providers
    that registered themselves at import time resolve with zero explicit
    wiring:

        import yokel.anthropic  # registers 'claude-*'
        from yokel.api import Yokel
        y = Yokel()
        response = y.model("claude-opus-4-8").user("Hello").send()

    Passing an explicit config dict returns an independent instance instead
    of the shared singleton -- the isolation path tests use to avoid
    cross-test state leakage.

    Args:
        config: A configuration dict merged over DEFAULT_CONFIG and applied
            to the instance's value_store. A "plugins" key, if present, is
            stripped before the merge is applied -- the plugins section is
            seeded only from the default provider registry, never from this
            dict. When None, the process-level singleton is returned/reused.
    """

    DEFAULT_CONFIG: dict[str, Any] = {}
    _instance: ClassVar[Yokel | None] = None

    def __new__(cls, config: dict[str, Any] | None = None) -> Yokel:
        if config is not None:
            return super().__new__(cls)

        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if config is None and getattr(self, "_config", None) is not None:
            return

        merged_config = {**self.DEFAULT_CONFIG, **(config or {})}
        merged_config.pop("plugins", None)

        manager = ConfigurationManager()
        for pattern, target in get_default_providers().items():
            manager.plugins.upsert(pattern, target)

        if merged_config:
            manager.value_store.patch(merged_config)

        self._config: ConfigurationManager = manager

    @property
    def conf(self) -> ConfigurationManager:
        """The ConfigurationManager owned by this instance.

        Exposed for advanced use and testing. Normal application code does not
        need to access this directly.
        """
        return self._config

    def model(self, model_id: str, *, max_tokens: int | None = None) -> MessageBuilder:
        """Resolve the provider for model_id and return a MessageBuilder.

        Provider resolution happens immediately. Raises UnknownModelError if no
        registered provider pattern matches model_id. Raises AuthError if the
        resolved provider fails authentication during construction.

        Args:
            model_id: The model identifier (e.g. ``"claude-opus-4-8"``).
            max_tokens: Upper bound on tokens the provider may generate. When
                None, the resolved provider's default_max_tokens is used.

        Returns:
            A MessageBuilder configured with the resolved provider, model_id,
            and effective max_tokens.

        Raises:
            UnknownModelError: No installed provider claims model_id.
            AuthError: Provider authentication failed at construction time.
        """
        provider = self._resolve_provider(model_id)
        effective_max_tokens = (
            max_tokens if max_tokens is not None else provider.default_max_tokens
        )
        return MessageBuilder(
            _provider=provider,
            _model=model_id,
            _max_tokens=effective_max_tokens,
            _system=None,
            _messages=(),
        )

    def _resolve_provider(self, model_id: str) -> Provider:
        """Iterate registered plugin patterns and return the first matching provider.

        Uses fnmatch.fnmatch for glob-style pattern matching (e.g. 'claude-*').
        First-registered-wins. Delegates instantiation to
        PluginConfigurationSection.activate().

        Raises:
            UnknownModelError: No pattern matched model_id.
        """
        for pattern in self._config.plugins.build():
            if fnmatch.fnmatch(model_id, pattern):
                return cast(
                    Provider,
                    self._config.plugins.activate(
                        pattern, value_store=self._config.value_store
                    ),
                )

        raise UnknownModelError(model_id)
