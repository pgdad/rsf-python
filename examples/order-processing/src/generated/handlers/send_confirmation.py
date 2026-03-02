"""Handler for the SendConfirmation task state."""

from rsf.registry import state


@state("SendConfirmation")
def send_confirmation(input_data: dict) -> dict:
    """Handler for the SendConfirmation task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement SendConfirmation handler")
