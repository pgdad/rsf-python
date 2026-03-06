"""Example RSF handler for the HelloWorld task state."""

from rsf.registry import state


@state("HelloWorld")
def hello_world(input_data: dict) -> dict:
    """Handle the HelloWorld state.

    Args:
        input_data: The input data for this state.

    Returns:
        The output to pass to the next state.
    """
    name = input_data.get("name", "World")
    return {"message": f"Hello, {name}!"}
