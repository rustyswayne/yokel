from typing import Any

from yokel.core.events import EventHandler


def test_can_register_event() -> None:
    # Arrange
    event_name = "test_name"

    # Act
    event_handler = EventHandler([event_name], False)

    # Assert
    assert event_handler.events_count == 1
    assert event_handler.is_event_registered(event_name)


def test_can_register_mulitple_events() -> None:
    # Arrange
    default_events = ["one", "two", "three"]
    supplimental = "four"

    ehandler = EventHandler(default_events, False)

    # Act
    ehandler.register(supplimental)

    # assert
    assert ehandler.events_count == 4
    assert ehandler.is_event_registered("one")
    assert ehandler.is_event_registered("three")
    assert ehandler.is_event_registered("two")
    assert ehandler.is_event_registered("four")


def test_can_register_a_callback() -> None:
    # Arrange
    event_name = "one"
    added = False
    results = []

    def on_one(*args: Any, **kwargs: Any) -> None:
        for arg in kwargs.values():
            results.append(arg)

    ehandler = EventHandler([event_name])

    # Act
    added = ehandler.link(on_one, "one")

    # assert
    assert ehandler.is_callback_in_event("one", on_one)
    assert added
    ehandler.emit("one", sender="test", value=1)
    assert len(results) == 2
    assert "test" in results
    assert 1 in results


def test_can_register_multiple_callbacks() -> None:
    # Arrange
    events = ["one", "two"]
    added_one1 = False
    added_one2 = False
    added_two = False
    resultsOne1 = []
    resultsOne2 = []
    results2 = {}

    def on_one1(*args: Any, **kwargs: Any) -> None:
        for arg in args:
            resultsOne1.append(arg)

    def on_one2(*args: Any, **kwargs: Any) -> None:
        values = [a for a in args if a != "skip"]
        for arg in values:
            resultsOne2.append(arg)

    def on_two(*args: Any, **kwargs: Any) -> None:
        for key in kwargs.keys():
            results2[key] = kwargs[key]

    ehandler = EventHandler(events)

    # Act
    added_one1 = ehandler.link(on_one1, "one")
    added_one2 = ehandler.link(on_one2, "one")
    added_two = ehandler.link(on_two, "two")

    ehandler.emit("one", "first", "second", "skip", "third")
    ehandler.emit("two", first=1, second=2, third=3)

    # Assert
    assert added_one1
    assert added_one2
    assert added_two
    assert len(resultsOne1) == 4
    assert len(resultsOne2) == 3
    assert len(results2.keys()) == 3
    assert "first" in resultsOne1 and "first" in resultsOne2
    assert "second" in resultsOne1 and "second" in resultsOne2
    assert "third" in resultsOne1 and "third" in resultsOne2
    assert "skip" in resultsOne1 and "skip" not in resultsOne2
    assert results2["first"] == 1
    assert results2["second"] == 2
    assert results2["third"] == 3


def test_can_register_and_link_event() -> None:
    # Arrange
    ehandler = EventHandler([])

    def test_callback(*args: Any, **kwargs: Any) -> None:
        pass

    # Act
    success = ehandler.register_link("one", test_callback)

    # Assert
    assert success
    assert ehandler.is_callback_in_event("one", test_callback)
    assert ehandler.is_event_registered("one")
