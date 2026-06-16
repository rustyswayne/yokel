from __future__ import annotations

from dataclasses import dataclass

from yokel.providers import Provider


@dataclass(frozen=True)
class MessageBuilder:
    """Immutable builder for a single LLM request.

    Every chain method returns a new MessageBuilder; the original is unchanged.
    This makes it safe to branch from a shared base configuration:

        base = y.model("claude-opus-4-8").system("You are helpful.")
        r1 = base.user("Question one").send()
        r2 = base.user("Question two").send()   # base is still unchanged

    Do not construct directly. Obtain via Yokel.model().
    """

    _provider: Provider
    _model: str
    _max_tokens: int
    _system: str | None
    _messages: tuple[dict[str, str], ...]
