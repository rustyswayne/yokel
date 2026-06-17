"""Optional live integration tests -- need a real API key."""

from __future__ import annotations

import importlib
import sys

import pytest
from yokel.anthropic._provider import AnthropicProvider
from yokel.api import Yokel


class TestLiveSend:
    """Live test against the real Anthropic API. Excluded from the default CI run."""

    @pytest.mark.requires_api_key
    def test_send_against_live_api_returns_response(self) -> None:
        """A real send() call returns a populated Response."""
        # Arrange
        provider = AnthropicProvider()

        # Act
        response = provider.send(
            messages=({"role": "user", "content": "Say 'ok' and nothing else."},),
            model="claude-haiku-4-5",
            system=None,
            max_tokens=16,
        )

        # Assert
        assert response.text, "live response should contain generated text"


class TestLiveYokelSend:
    """Live test against the real Anthropic API through the Yokel public API."""

    @pytest.mark.requires_api_key
    def test_yokel_model_send_against_live_api_returns_response(self) -> None:
        """Yokel().model("claude-*") resolves AnthropicProvider via import-time
        registration, and .user(...).send() returns a populated Response.
        """
        # Arrange -- re-import to re-apply registration cleared by the
        # autouse reset_yokel_singleton_and_registry fixture
        sys.modules.pop("yokel.anthropic", None)
        importlib.import_module("yokel.anthropic")

        y = Yokel()
        builder = y.model("claude-haiku-4-5", max_tokens=16)
        assert isinstance(builder._provider, AnthropicProvider)

        # Act
        response = builder.user("Say 'ok' and nothing else.").send()

        # Assert
        assert response.text, "live response should contain generated text"
