"""Tests for yokel.anthropic: import-time default registration, register()."""

from __future__ import annotations

import importlib
import sys

import pytest
import yokel.anthropic
from yokel._registry import get_default_providers
from yokel.api import Yokel
from yokel.core.configuration.manager import ConfigurationManager


class TestImportTimeRegistration:
    """Tests for the import-time default registration (path a)."""

    def test_importing_module_registers_claude_pattern(self) -> None:
        """Re-importing yokel.anthropic re-applies the default registration."""
        # Arrange
        sys.modules.pop("yokel.anthropic", None)

        # Act
        importlib.import_module("yokel.anthropic")

        # Assert
        assert get_default_providers() == {
            "claude-*": "yokel.anthropic, AnthropicProvider"
        }, "import should register claude-* in the default registry"

    def test_yokel_singleton_resolves_claude_model_after_import(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A fresh Yokel() resolves claude-* with zero explicit wiring."""
        # Arrange
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
        sys.modules.pop("yokel.anthropic", None)
        importlib.import_module("yokel.anthropic")

        # Act
        y = Yokel()
        builder = y.model("claude-opus-4-8", max_tokens=10)

        # Assert
        assert isinstance(builder._provider, yokel.anthropic.AnthropicProvider), (
            "Yokel().model('claude-*') should resolve to AnthropicProvider"
        )


class TestRegister:
    """Tests for yokel.anthropic.register (path b, isolation)."""

    def test_register_writes_pattern_into_given_configuration_manager(self) -> None:
        """register() upserts claude-* directly into a ConfigurationManager."""
        # Arrange
        manager = ConfigurationManager()

        # Act
        yokel.anthropic.register(manager)

        # Assert
        assert (
            manager.plugins.get("claude-*") == "yokel.anthropic, AnthropicProvider"
        ), "register() should upsert the claude-* pattern into the given manager"

    def test_register_writes_pattern_into_given_yokel_instance(self) -> None:
        """register() accepts a Yokel instance and writes into its manager."""
        # Arrange
        y = Yokel(config={})

        # Act
        yokel.anthropic.register(y)

        # Assert
        assert y.conf.plugins.get("claude-*") == "yokel.anthropic, AnthropicProvider", (
            "register() should upsert claude-* into the Yokel instance's manager"
        )

    def test_register_does_not_touch_default_registry(self) -> None:
        """register() is isolation-only -- never mutates the process-level registry."""
        # Arrange
        manager = ConfigurationManager()

        # Act
        yokel.anthropic.register(manager)

        # Assert
        assert get_default_providers() == {}, (
            "register() must not write to the default provider registry"
        )
