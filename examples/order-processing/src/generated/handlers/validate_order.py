"""Handler for the ValidateOrder task state."""

from rsf.registry import state


@state("ValidateOrder")
def validate_order(input_data: dict) -> dict:
    """Handler for the ValidateOrder task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement ValidateOrder handler")
