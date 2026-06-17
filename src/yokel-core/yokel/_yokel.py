from __future__ import annotations

import fnmatch
from typing import Any, cast

from yokel._builder import MessageBuilder
from yokel.core.configuration.manager import ConfigurationManager
from yokel.core.errors import UnknownModelError
from yokel.providers import Provider


class Yokel:
    """Primary entry point for the yokel library.

    Instantiate once and reuse. Owns the ConfigurationManager that holds
    plugin registrations and the value store.

    Providers register themselves at import time. Import the provider package
    before calling model():

        import yokel.anthropic  # registers 'claude-*'
        from yokel.api import Yokel
        y = Yokel()
        response = y.model("claude-opus-4-8").user("Hello").send()

    Args:
        config: An existing ConfigurationManager to use. When None, a default
            manager is constructed automatically.
    """

    DEFAULT_CONFIG: dict[str, Any] = {}

    def __init__(self, config: ConfigurationManager | None = None) -> None:
        self._config: ConfigurationManager = (
            ConfigurationManager() if config is None else config
        )

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
