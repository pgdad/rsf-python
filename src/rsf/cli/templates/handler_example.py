"""Example RSF handler using the @state decorator."""

from rsf.functions.decorators import state


@state("HelloWorld")
def hello_world(event: dict, context: dict) -> dict:
    """Handle the HelloWorld state.

    Args:
        event: The input event for this state.
        context: The Lambda execution context.

    Returns:
        The output to pass to the next state.
    """
    name = event.get("name", "World")
    return {"message": f"Hello, {name}!"}
