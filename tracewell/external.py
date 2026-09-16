"""External trace conformance and evaluation path.

See ADR-0016 and docs/ARCHITECTURE.md §34.
"""

from __future__ import annotations

from pydantic import ValidationError

from .comparator import compare_pair, required_constructs
from .evaluator import evaluate_case
from .models import BehaviorDeltaResult, CasePair, Trace


class TraceConformanceError(ValueError):
    pass


def parse_external_trace(payload: dict, *, expected_case_id: str) -> Trace:
    """Validate an externally supplied trace without guessing missing events."""
    try:
        trace = Trace.model_validate(payload)
    except ValidationError as exc:
        raise TraceConformanceError(str(exc)) from exc
    if trace.case_id != expected_case_id:
        raise TraceConformanceError(
            f"trace case_id {trace.case_id!r} does not match expected case {expected_case_id!r}"
        )
    if not trace.events:
        raise TraceConformanceError("external trace must contain at least one observable event")
    return trace


def evaluate_external_pair(
    pair: CasePair,
    canonical_trace: Trace,
    perturbed_trace: Trace,
) -> BehaviorDeltaResult:
    """Route external traces through the same evaluator and comparator path."""
    if canonical_trace.case_id != pair.canonical_case.case_id:
        raise TraceConformanceError("canonical trace case_id mismatch")
    if perturbed_trace.case_id != pair.perturbed_case.case_id:
        raise TraceConformanceError("perturbed trace case_id mismatch")

    constructs = required_constructs(pair)
    canonical_results = evaluate_case(pair.canonical_case, canonical_trace, constructs)
    perturbed_results = evaluate_case(pair.perturbed_case, perturbed_trace, constructs)
    return compare_pair(pair, canonical_results, perturbed_results)
