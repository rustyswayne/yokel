import os
import sys
from pathlib import Path

import pytest

current_dir = Path(__file__).parent
module_paths = [
    current_dir / "..",  # The current project under test
    current_dir / ".." / ".." / "yokel-core",  # yokel-core, for yokel.core/_yokel
]

for path in module_paths:
    abs_path = path.resolve()  # Get absolute path
    if str(abs_path) not in sys.path:
        sys.path.insert(0, str(abs_path))


sys.path.insert(0, os.path.dirname(__file__))


@pytest.fixture(autouse=True)
def reset_yokel_singleton_and_registry() -> None:
    """Reset the Yokel singleton and default provider registry between tests."""
    from yokel import _registry
    from yokel._yokel import Yokel

    Yokel._instance = None
    _registry._default_registry.clear()


@pytest.fixture(autouse=True)
def clear_anthropic_api_key_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ANTHROPIC_API_KEY from the real environment never leaks into tests."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
