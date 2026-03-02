"""Handler for the RequireApproval task state."""

from rsf.registry import state


@state("RequireApproval")
def require_approval(input_data: dict) -> dict:
    """Handler for the RequireApproval task state.

    Implement your business logic here.
    """
    raise NotImplementedError("Implement RequireApproval handler")
