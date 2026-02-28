"""Example tests for RSF handlers."""

from handlers.example_handler import hello_world


def test_hello_world_default() -> None:
    """Handler returns default greeting when no name is provided."""
    result = hello_world({}, {})
    assert result == {"message": "Hello, World!"}


def test_hello_world_with_name() -> None:
    """Handler returns personalized greeting when name is provided."""
    result = hello_world({"name": "RSF"}, {})
    assert result == {"message": "Hello, RSF!"}
