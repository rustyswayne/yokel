import yaml
import importlib
from copy import deepcopy
from typing import Dict, Any, Optional, Callable, Sequence, cast
from .interfaces import (
    IConfigurationManager,
    IConfigurationContainer,
    IConfigurationSection,
    IPluginConfigurationSection,
    EVENT_CONFIGURATION_CHANGED,
    EVENT_CONFIGURATION_CHANGING,
)
from ..events import EventHandler


def default_get_parent_callable() -> Dict[str, Any]:
    """Return the default parent configuration."""
    return {}


class AbstractConfigurationContainer(IConfigurationContainer):
    """An abstract base class for configuration containers."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__()
        self._config: Dict[str, Any] = config or {}

    def get(self, key: str) -> Any | None:
        """Retrieve the configuration value for a given key."""
        return self._config.get(key)

    def show(self, pattern: Optional[Callable[[str, Any], bool]] = None) -> None:
        """Display the current configuration."""
        if pattern is None:
            pattern = lambda k, v: True  # noqa: E731

        matched: Dict[str, Any] = {}
        for key, value in self._config.items():
            if pattern(key, value):
                matched[key] = value

        print(yaml.dump(matched, default_flow_style=False, sort_keys=False))


class ConfigurationSection(AbstractConfigurationContainer, IConfigurationSection):
    """A configuration section."""

    def __init__(
        self, section_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(config)
        self.__section_name = section_name
        self.__get_parent_callable: Callable[[], Dict[str, Any]] = (
            default_get_parent_callable
        )
        self.__ehandler: EventHandler = EventHandler(
            [EVENT_CONFIGURATION_CHANGING, EVENT_CONFIGURATION_CHANGED], False
        )

    @property
    def section_name(self) -> str:
        """Get the name of the configuration section."""
        return self.__section_name

    def build(self) -> Dict[str, Any]:
        """Build the configuration from a dictionary."""
        built: Dict[str, Any] = self.__get_parent_callable()
        built.update(self._config)
        return built

    def upsert(self, key: str, value: Any) -> None:
        """Insert or updates the configuration for a given key."""
        if not isinstance(key, str):
            raise TypeError("Key must be a string.")

        self.__ehandler.emit(EVENT_CONFIGURATION_CHANGING, key, value)
        self._config[key] = value
        self.__ehandler.emit(EVENT_CONFIGURATION_CHANGED, deepcopy(self._config))

    def patch(self, values: Dict[str, Any]) -> None:
        """Patches the configuration with the provided values."""
        if not isinstance(values, dict):
            raise TypeError("Values must be a dictionary.")

        for key, value in values.items():
            self.upsert(key, value)

        self.__ehandler.emit(EVENT_CONFIGURATION_CHANGED, deepcopy(self._config))

    def show(self, pattern: Optional[Callable[[str, Any], bool]] = None) -> None:
        """Display the current configuration."""
        print(f"Configuration for section '{self.section_name}':")
        super().show(pattern)

    def set_parent_callable(self, parent_func: Callable[[], Dict[str, Any]]) -> None:
        """Set the parent callable that provides additional configuration."""
        if parent_func is None or not callable(parent_func):
            raise TypeError("Parent callable must be a callable function.")

        self.__get_parent_callable = parent_func

    def on_configuration_changing(  # noqa: FNE005
        self, func: Callable[[str, Any], None]
    ) -> bool:
        """Register a function to be called when the configuration is changing."""
        if not callable(func):
            raise TypeError("Function must be callable.")

        return self.__ehandler.link(func, EVENT_CONFIGURATION_CHANGING)

    def on_configuration_changed(  # noqa: FNE005
        self, func: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """Register a function to be called when the configuration has changed."""
        if not callable(func):
            raise TypeError("Function must be callable.")

        return self.__ehandler.link(func, EVENT_CONFIGURATION_CHANGED)


class StringConfigurationSection(ConfigurationSection):
    """A configuration section that only accepts string values."""

    def __init__(
        self, section_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        super().__init__(section_name, config)
        self.on_configuration_changing(lambda _, value: self.__validate_value(value))

    def __validate_value(self, value: Any) -> None:
        """Validate that the value is a string."""
        if not isinstance(value, str):
            raise ValueError("Configuration values must be strings.")


class PluginConfigurationSection(ConfigurationSection, IPluginConfigurationSection):
    """A configuration section specifically for plugins."""

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__("plugins", config)
        self.on_configuration_changing(lambda _, value: self.__validate_value(value))

    def activate(self, key: str, *args, **kwargs) -> None:
        """Activates the plugin configuration section."""
        module_class = self.get(key)
        if not isinstance(module_class, str):
            raise TypeError(
                f"Plugin configuration for '{key}' must be a string in the format 'module_name, class_name'."
            )

        split = module_class.rsplit(",", 1)
        module_name = split[0].strip()
        class_name = split[1].strip()
        return self.__get_instance(class_name, module_name, *args, **kwargs)

    def __get_instance(
        self,
        class_name: str,
        module_name: str,
        *args,
        **kwargs,
    ) -> Any:
        """Get an instance of a class."""
        module = importlib.import_module(module_name)
        class_ = getattr(module, class_name)
        return class_(*args, **kwargs)

    def __validate_value(self, value: Any) -> None:
        """Validate the value for the plugin configuration."""
        if value is None or isinstance(value, str) is False:
            raise ValueError(
                "Plugin configuration values must be strings in the format 'module_name, class_name'."
            )

        split = value.rsplit(",", 1)
        if len(split) != 2 or not all(part.strip() for part in split):
            raise ValueError(
                "Plugin configuration values must be in the format 'module_name, class_name'."
            )


class ConfigurationManager(IConfigurationManager):
    """A configuration manager that manages multiple configuration sections."""

    def __init__(
        self, sections: Optional[Sequence[IConfigurationSection]] = None
    ) -> None:
        super().__init__()
        self.__sections: Dict[str, IConfigurationSection] = {}
        self.__load_sections(sections or [])

    @property
    def plugins(self) -> IPluginConfigurationSection:
        """Retrieves the plugins configuration section."""
        return cast(IPluginConfigurationSection, self.get_section("plugins"))

    @property
    def value_store(self) -> IConfigurationSection:  # noqa: FNE002
        """Retrieve the value store configuration section."""
        return self.get_section("value_store")

    def get_section(self, section_name: str) -> IConfigurationSection:
        """Retrieve a configuration section by name."""
        if section_name not in self.__sections:
            raise KeyError(f"Section '{section_name}' not found.")

        return self.__sections[section_name]

    def register_new_section(
        self, section_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a new configuration section."""
        if section_name in self.__sections:
            raise ValueError(f"Section '{section_name}' already exists.")

        section = ConfigurationSection(section_name, config)
        self.register_section(section)

    def register_section(self, section: IConfigurationSection) -> None:
        """Register a configuration section."""
        if not isinstance(section, IConfigurationSection):
            raise TypeError("Section must be an instance of IConfigurationSection.")

        if section.section_name in self.__sections:
            raise ValueError(f"Section '{section.section_name}' already exists.")

        self.__sections[section.section_name] = section

    def clear(self) -> None:
        """Clear all configuration sections."""
        self.__sections.clear()
        self.__load_sections([])

    def __load_sections(self, sections: Sequence[IConfigurationSection]) -> None:
        """Load multiple configuration sections."""
        for section in sections:
            if not isinstance(section, IConfigurationSection):
                raise TypeError(
                    "All sections must be instances of IConfigurationSection."
                )

            if (
                section.section_name == "plugins"
                and isinstance(section, IPluginConfigurationSection) is False
            ):
                raise TypeError(
                    "The 'plugins' section must be an instance of IPluginConfigurationSection."
                )

            self.__sections[section.section_name] = section

        if "plugins" not in self.__sections:
            self.__sections["plugins"] = PluginConfigurationSection()

        if "value_store" not in self.__sections:
            self.__sections["value_store"] = ConfigurationSection("value_store")
