import types
from typing import Callable, List, Dict, Any


class EventHandler:
    """
    Represents a simple event handler class for synchronous event implementations based registered callback functions.

    Based on (MIT):
        https://github.com/davidvicenteranz/eventhandler/blob/master/eventhandler/__init__.py
    """

    def __init__(self, event_names: list[str], swallow_exceptions: bool = True) -> None:
        self.__events: Dict[str, List[Callable]] = {}
        self.__swallow_exceptions: bool = swallow_exceptions
        if event_names:
            for event in event_names:
                self.register(str(event))

    @property
    def events(self) -> Dict[str, List[Callable]]:
        """Return events as a dictionary."""
        return self.__events

    @property
    def event_list(self) -> List[str]:  # noqa: FNE002
        """Return list of registered events."""
        return list(self.__events.keys())

    @property
    def events_count(self) -> int:  # noqa: FNE002
        """Return number of registered events."""
        return len(self.event_list)

    @staticmethod
    def is_callable(func: Any) -> bool:
        """
        Return true if func is a callable/functions.

        Args:
            func (any): The variable to test if it's a callable.

        Returns:
            bool: A value indicating whether or not func is a callable.
        """
        return isinstance(
            func,
            (
                types.FunctionType,
                types.BuiltinFunctionType,
                types.MethodType,
                types.BuiltinMethodType,
            ),
        )

    def clear_events(self) -> bool:  # noqa: FNE005
        """Clear all events."""
        self.__events = {}
        return True

    def register(self, event_name: str) -> bool:  # noqa: FNE005
        """
        Register an event to which callbacks can be associated.

        Args:
            event_name (str): The name of the event.

        Returns:
            bool: A value indicating if the event was registered successfully.
        """
        if event_name in self.__events:
            return False

        self.__events[event_name] = []
        return True

    def register_link(  # noqa: FNE005
        self, event_name: str, callback: Callable
    ) -> bool:
        """
        Register an event with a callback.

        Args:
            event_name (str): The event name.
            callback (callable): The function to link.

        Returns:
            bool: A value indicating whether or not the registration was successful.
        """
        if not self.is_event_registered(event_name) and not self.register(event_name):
            return False

        return self.link(callback, event_name)

    def unregister(self, event_name: str) -> bool:  # noqa: FNE005
        """
        Remove an event registration.

        Args:
            event_name (str): The event name.

        Returns:
            bool: A value indicating whether or not the event was removed from the registrations.
        """
        if event_name in self.__events:
            del self.__events[event_name]
            return True

        return False

    def is_event_registered(self, event_name: str) -> bool:
        """
        Return if an event is current registered.

        Args:
            event_name (str): The event you want to consult.
        """
        return event_name in self.__events

    def is_callback_in_event(self, event_name: str, callback: Callable) -> bool:
        """
        Return if a given callback is already registered on the events dict.

        Args:
            event_name (str): The event name to look up for the callback inside.
            callback (callable): The callback function to check.

        Returns:
            bool: A value indicating whether or not a given callback is already registered on the events dict.
        """
        return callback in self.__events[event_name]

    def link(self, callback: Callable, event_name: str) -> bool:  # noqa: FNE005
        """
        Link a callback to be executed on fired event..

        Args:
            callback (callable): function to link.
            event_name (str): The event that will trigger the callback execution.

        Returns:
            bool: A value indicating whether or not a given callback was linked.
        """
        if not self.is_callable(callback):
            return False

        if not self.is_event_registered(event_name):
            return False

        if callback not in self.__events[event_name]:
            self.__events[event_name].append(callback)
            return True

        return False

    def unlink(self, callback: Callable, event_name: str) -> bool:  # noqa: FNE005
        """
        Unlink a callback execution from a specific event.

        Args:
            callback (callable): function to link.
            event_name (str): The event that will trigger the callback execution.

        Returns:
            bool: A value indicating whether or not the callback was unlinked
            from the event.
        """
        if not self.is_event_registered(event_name):
            return False

        if callback in self.__events[event_name]:
            self.__events[event_name].remove(callback)
            return True

        return False

    def emit(self, event_name: str, *args, **kwargs) -> bool:  # noqa: FNE005
        """
        Triggers all callback executions linked to the given event.

        Args:
            event_name (str): Event to trigger.
            *args: Arguments to be passed to callback functions execution.
            *kwargs: Keyword arguments to be passed to callback functions execution.

        Returns:
            bool: A value indicating if the event was emitted.
        """
        success = True

        for callback in self.__events[event_name]:
            try:
                callable(callback(*args, **kwargs))
            except Exception as e:
                if not self.__swallow_exceptions:
                    raise e

                success = False
                continue

        return success
