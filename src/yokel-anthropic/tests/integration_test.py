"""Optional live integration test for AnthropicProvider.send -- needs a real API key."""

from __future__ import annotations

import pytest
from yokel.anthropic._provider import AnthropicProvider


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
