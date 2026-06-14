import pytest
from typing import Any
from yokel.configuration.manager import PluginConfigurationSection


def test_plugin_configuration_section_initialization() -> None:
    """Test that PluginConfigurationSection can be initialized."""
    # Arrange
    section = PluginConfigurationSection()

    # Act & Assert
    assert section.section_name == "plugins"
    assert section.build() == {}
    assert section.get("non_existent_key") is None


@pytest.mark.parametrize(
    "key, value",
    [
        ("plugin1", "Class1"),
        ("plugin2", 123),
        ("plugin3", None),
    ],
)
def test_adding_invalid_plugin_configuration_raises_type_error(
    key: str, value: Any
) -> None:
    """Test that adding an invalid plugin configuration raises TypeError."""
    # Arrange
    section = PluginConfigurationSection()

    # Act & Assert
    with pytest.raises(ValueError):
        section.upsert(key, value)  # Not a string


def test_adding_valid_plugin_configuration() -> None:
    """Test that adding a valid plugin configuration works."""
    # Arrange
    section = PluginConfigurationSection()
    valid_plugin = "module_name, ClassName"

    # Act
    section.upsert("valid_plugin", valid_plugin)

    # Assert
    assert section.get("valid_plugin") == valid_plugin
