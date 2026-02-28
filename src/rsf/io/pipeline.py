"""5-stage JSONPath I/O processing pipeline.

Pipeline stages:
  Raw Input → InputPath → Parameters → [Task Execution] → ResultSelector → ResultPath → OutputPath → Final Output

Critical invariant: ResultPath merges into the RAW input, not the effective input.
"""

from __future__ import annotations

from typing import Any

from rsf.io.jsonpath import evaluate_jsonpath
from rsf.io.payload_template import apply_payload_template
from rsf.io.result_path import apply_result_path
from rsf.io.types import VariableStoreProtocol


def process_jsonpath_pipeline(
    raw_input: Any,
    task_result: Any,
    input_path: str | None = None,
    parameters: dict[str, Any] | None = None,
    result_selector: dict[str, Any] | None = None,
    result_path: str | None = "$",
    output_path: str | None = None,
    context: Any | None = None,
    variables: VariableStoreProtocol | None = None,
    intrinsic_evaluator: Any | None = None,
) -> Any:
    """Execute the 5-stage I/O pipeline.

    Args:
        raw_input: The original input to the state.
        task_result: The result returned by the task execution.
        input_path: JSONPath to filter raw input (Stage 1).
        parameters: Payload template for effective input (Stage 2).
        result_selector: Payload template for task result (Stage 3).
        result_path: Where to merge result into raw input (Stage 4). Defaults to "$".
        output_path: JSONPath to filter final output (Stage 5).
        context: ASL context object for $$ references.
        variables: Variable store for $varName references.
        intrinsic_evaluator: Callable for intrinsic function evaluation.

    Returns:
        The final output after all pipeline stages.
    """
    # Stage 1: InputPath filters raw_input → effective_input
    if input_path is not None:
        effective_input = evaluate_jsonpath(raw_input, input_path, variables=variables, context=context)
    else:
        effective_input = raw_input

    # Stage 2: Parameters payload template on effective_input
    if parameters is not None:
        effective_input = apply_payload_template(parameters, effective_input, context, variables, intrinsic_evaluator)

    # Stage 3: ResultSelector payload template on task_result
    effective_result = task_result
    if result_selector is not None:
        effective_result = apply_payload_template(result_selector, task_result, context, variables, intrinsic_evaluator)

    # Stage 4: ResultPath merges into RAW input (not effective!)
    merged = apply_result_path(raw_input, effective_result, result_path)

    # Stage 5: OutputPath filters merged output
    if output_path is not None:
        return evaluate_jsonpath(merged, output_path, variables=variables, context=context)

    return merged
