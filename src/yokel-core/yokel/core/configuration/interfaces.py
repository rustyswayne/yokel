import abc
from typing import Any, Callable, Dict, Optional, cast

EVENT_CONFIGURATION_CHANGING = "configuration_changing"
EVENT_CONFIGURATION_CHANGED = "configuration_changed"


class IConfigurationContainer(metaclass=abc.ABCMeta):
    """Represents a container for configuration sections."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if (
            hasattr(subclass, "build")
            and callable(subclass.build)
            and hasattr(subclass, "get")
            and callable(subclass.get)
            and hasattr(subclass, "upsert")
            and callable(subclass.upsert)
            and hasattr(subclass, "patch")
            and callable(subclass.patch)
            and hasattr(subclass, "show")
            and callable(subclass.show)
        ):
            return True

        return cast(bool, NotImplemented)

    @abc.abstractmethod
    def build(self) -> Dict[str, Any]:
        """Build the configuration from a dictionary."""
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, key: str) -> Any | None:
        """Retrieve the configuration for a given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def upsert(self, key: str, value: Any) -> None:
        """Insert or updates the configuration for a given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def patch(self, values: Dict[str, Any]) -> None:
        """Patche the configuration for a given key."""
        raise NotImplementedError

    @abc.abstractmethod
    def show(self, pattern: Optional[Callable[[str, Any], bool]] = None) -> None:
        """Display the current configuration."""
        raise NotImplementedError


class IConfigurationSection(IConfigurationContainer):
    """Represents a section of configuration."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if (
            hasattr(subclass, "section_name")
            and hasattr(subclass, "set_parent_callable")
            and callable(subclass.set_parent_callable)
            and hasattr(subclass, "on_configuration_changing")
            and callable(subclass.on_configuration_changing)
            and hasattr(subclass, "on_configuration_changed")
            and callable(subclass.on_configuration_changed)
        ):
            return True

        return cast(bool, NotImplemented)

    @property
    @abc.abstractmethod
    def section_name(self) -> str:
        """Get the name of the configuration section."""
        raise NotImplementedError

    @abc.abstractmethod
    def set_parent_callable(self, parent_func: Callable[[], Dict[str, Any]]) -> None:
        """Set a function to get the parent configuration."""
        raise NotImplementedError

    @abc.abstractmethod
    def on_configuration_changing(  # noqa: FNE005
        self, func: Callable[[str, Any], None]
    ) -> bool:
        """Call when the configuration is about to change."""
        raise NotImplementedError

    @abc.abstractmethod
    def on_configuration_changed(  # noqa: FNE005
        self, func: Callable[[Dict[str, Any]], None]
    ) -> bool:
        """Call when the configuration has changed."""
        raise NotImplementedError


class IPluginConfigurationSection(IConfigurationSection):
    """Represents a plugin configuration section."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if hasattr(subclass, "activate") and callable(subclass.activate):
            return True

        return cast(bool, NotImplemented)

    @abc.abstractmethod
    def activate(self, key: str, *args: Any, **kwargs: Any) -> Any:
        """Activates the configured plugin."""
        raise NotImplementedError


class IConfigurationManager(metaclass=abc.ABCMeta):
    """Represents a configuration manager."""

    @classmethod
    def __subclasshook__(cls, subclass: type) -> bool:  # noqa: D105, FNE005
        if (
            hasattr(subclass, "plugins")
            and hasattr(subclass, "value_store")
            and hasattr(subclass, "get_section")
            and callable(subclass.get_section)
            and hasattr(subclass, "create_new_section")
            and callable(subclass.create_new_section)
            and hasattr(subclass, "register_section")
            and callable(subclass.register_section)
            and hasattr(subclass, "clear")
            and callable(subclass.clear)
        ):
            return True

        return cast(bool, NotImplemented)

    @property
    @abc.abstractmethod
    def plugins(self) -> IPluginConfigurationSection:
        """Return the plugin configuration section."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def value_store(self) -> IConfigurationSection:  # noqa: FNE002
        """Return the value store configuration section."""
        raise NotImplementedError

    @abc.abstractmethod
    def get_section(self, section_name: str) -> IConfigurationSection:
        """Retrieve a configuration section by name."""
        raise NotImplementedError

    @abc.abstractmethod
    def register_new_section(
        self, section_name: str, config: Optional[Dict[str, Any]] = None
    ) -> None:
        """Create a new configuration section."""
        raise NotImplementedError

    @abc.abstractmethod
    def register_section(self, section: IConfigurationSection) -> None:
        """Register a new configuration section."""
        raise NotImplementedError
