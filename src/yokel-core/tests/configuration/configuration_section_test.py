from typing import Any, Dict

import pytest
from yokel.core.configuration.manager import ConfigurationSection


@pytest.mark.parametrize(
    "section_name, config",
    [
        ("name_only_section", None),
        ("empty_section", {}),
        (
            "simple_section",
            {
                "key1": "value1",
                "key2": 42,
                "key3": True,
            },
        ),
        (
            "complex_section",
            {
                "sub_key": {
                    "sub_key1": "sub_value1",
                    "sub_key2": 3.14,
                },
                "array_key": [1, 2, 3],
            },
        ),
    ],
)
def test_can_instantiate_configuration_section(
    section_name: str, config: Dict[str, Any]
) -> None:
    """Test that we can instantiate a ConfigurationSection."""

    # Arrange
    # Act
    section = ConfigurationSection(section_name, config)

    # Assert
    assert section.section_name == section_name
    assert section.build() == (config or {})
    if config is not None:
        for key, value in config.items():
            assert section.get(key) == value


def test_show_does_not_raise() -> None:
    """Test that show does not raise an exception."""
    # Arrange
    section = ConfigurationSection("test_section", {"key1": "value1"})

    # Act & Assert
    try:
        section.show()
    except Exception as e:
        pytest.fail(f"show raised an exception: {e}")


def test_upsert_raises_with_non_string_key() -> None:
    """Test that upsert raises TypeError with non-string key."""
    # Arrange
    section = ConfigurationSection("test_section")

    # Act & Assert
    with pytest.raises(TypeError, match="Key must be a string."):
        section.upsert(123, "value")  # type: ignore # Non-string key


def test_can_upsert_a_new_value() -> None:
    """Test that we can upsert a new value."""
    # Arrange
    section = ConfigurationSection("test_section")

    # Act
    section.upsert("new_key", "new_value")

    # Assert
    assert section.get("new_key") == "new_value"


def test_can_upsert_an_existing_value() -> None:
    """Test that we can upsert an existing value."""
    # Arrange
    section = ConfigurationSection("test_section", {"existing_key": "old_value"})

    # Act
    section.upsert("existing_key", "new_value")

    # Assert
    assert section.get("existing_key") == "new_value"


def test_can_patch_values() -> None:
    """Test that we can patch values."""
    # Arrange
    additional_key = "additional_key"
    additional_value = "additional_value"
    section = ConfigurationSection(
        "test_section", {"key1": "value1", "key2": "value2", "key3": 10}
    )

    # Act
    section.patch({"key2": "value2", "key3": 42, additional_key: additional_value})

    # Assert
    assert section.get("key1") == "value1"
    assert section.get("key2") == "value2"
    assert section.get("key3") == 42
    assert section.get(additional_key) == additional_value


def test_build_returns_combined_configuration() -> None:
    """Test that build returns the combined configuration."""
    # Arrange
    parent_config = {"parent_key": "parent_value"}
    section = ConfigurationSection("test_section", {"key1": "value1"})
    section.set_parent_callable(lambda: parent_config)

    # Act
    built_config = section.build()

    # Assert
    assert built_config == {"parent_key": "parent_value", "key1": "value1"}


def test_on_configuration_changing_and_changed() -> None:
    """Test that on_configuration_changing and on_configuration_changed work."""
    # Arrange
    section = ConfigurationSection("test_section")
    changing_called = False
    changed_called = False

    def on_changing(key: str, value: Any) -> None:
        nonlocal changing_called
        changing_called = True

    def on_changed(config: Dict[str, Any]) -> None:
        nonlocal changed_called
        changed_called = True

    section.on_configuration_changing(on_changing)
    section.on_configuration_changed(on_changed)

    # Act
    section.upsert("key", "value")

    # Assert
    assert changing_called
    assert changed_called
