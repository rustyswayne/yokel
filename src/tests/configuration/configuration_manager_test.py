import pytest
from typing import Sequence
from yokel.configuration.manager import (
    ConfigurationManager,
    ConfigurationSection,
    PluginConfigurationSection,
    StringConfigurationSection,
)
from yokel.configuration.interfaces import (
    IConfigurationManager,
    IConfigurationSection,
    IPluginConfigurationSection,
)


@pytest.mark.parametrize(
    "sections",
    [
        ([ConfigurationSection("custom")]),
        (
            ConfigurationSection("some_section", {"key": "value"}),
            ConfigurationSection("value_store", {"key": "value"}),
        ),
        (
            PluginConfigurationSection({"plugin1": "value1"}),
            ConfigurationSection("value_store", {"store_key": "store_value"}),
            ConfigurationSection("jinja_parameters", {"param1": "value1"}),
            StringConfigurationSection("jinja_macros", {"macro1": "value1"}),
        ),
        None,
    ],
)
def test_configuration_manager_initialization(
    sections: Sequence[IConfigurationSection],
) -> None:
    """Test that ConfigurationManager can be initialized with no sections."""
    # Arrange & Act
    manager = ConfigurationManager(sections)

    # Assert
    assert isinstance(manager, IConfigurationManager)
    assert manager.plugins is not None
    assert manager.value_store is not None


def test_configuration_manager_get_section() -> None:
    """Test that ConfigurationManager can retrieve a section by name."""
    # Arrange
    section_name = "test_section"
    section = ConfigurationSection(section_name, {"key": "value"})
    manager = ConfigurationManager([section])

    # Act
    retrieved_section = manager.get_section(section_name)

    # Assert
    assert retrieved_section.section_name == section_name
    assert retrieved_section.get("key") == "value"


def test_configuration_manager_register_new_section() -> None:
    """Test that ConfigurationManager can register a new section."""
    # Arrange
    section_name = "new_section"
    config = {"key": "value"}
    manager = ConfigurationManager()

    # Act
    manager.register_new_section(section_name, config)
    new_section = manager.get_section(section_name)

    # Assert
    assert new_section.section_name == section_name
    assert new_section.get("key") == "value"


def test_configuration_manager_register_existing_section_raises_exception() -> None:
    """Test that ConfigurationManager raises an error when registering an existing section."""
    # Arrange
    section_name = "existing_section"
    config = {"key": "value"}
    manager = ConfigurationManager([ConfigurationSection(section_name, config)])

    # Act & Assert
    with pytest.raises(ValueError, match=f"Section '{section_name}' already exists."):
        manager.register_new_section(section_name, {"new_key": "new_value"})


def test_configuration_manager_clear() -> None:
    """Test that ConfigurationManager can clear all sections."""
    # Arrange
    section1 = ConfigurationSection("section1", {"key1": "value1"})
    section2 = ConfigurationSection("section2", {"key2": "value2"})
    manager = ConfigurationManager([section1, section2])

    # Act
    manager.clear()

    # Assert
    section_count = len(getattr(manager, "_ConfigurationManager__sections"))
    assert section_count == 2  # Only default sections remain
    with pytest.raises(KeyError):
        manager.get_section("section1")


def test_plugin_configuration_section_is_typed() -> None:
    """Test that PluginConfigurationSection can be initialized and used."""
    # Arrange
    manager = ConfigurationManager()

    # Act
    plugin_section = manager.plugins

    # Assert
    assert isinstance(plugin_section, IPluginConfigurationSection)
