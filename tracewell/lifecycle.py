"""SafetyFinding and paired mitigation-verification lifecycle.

See docs/EVALUATION_SPEC.md §§21–23 and ADR-0009.
"""

from __future__ import annotations

from dataclasses import dataclass

from .comparator import compare_pair, required_constructs
from .evaluator import evaluate_case
from .models import BehaviorDeltaResult, CasePair, FindingStatus, SafetyFinding, Verdict
from .reference_agent import AgentMode, ReferenceAgent


@dataclass(frozen=True)
class VerificationOutcome:
    finding: SafetyFinding
    result: BehaviorDeltaResult


def create_finding(
    pair: CasePair,
    result: BehaviorDeltaResult,
    *,
    finding_id: str | None = None,
) -> SafetyFinding | None:
    """Create a regression finding only for an established pair FAIL."""
    if result.pair_result != Verdict.FAIL:
        return None

    return SafetyFinding(
        finding_id=finding_id or f"{pair.pair_id}:finding",
        pair_id=pair.pair_id,
        case_family=pair.canonical_case.scenario_family,
        failure_type=_failure_type(result),
        expected_changes=result.expected_changes,
        observed_changes=result.observed_changes,
        invariant_violations=result.invariant_violations,
        evidence_refs=result.evidence_refs,
        status=FindingStatus.OPEN,
    )


def record_mitigation(
    finding: SafetyFinding,
    *,
    proposed_mitigation: str,
    closure_criteria: str,
) -> SafetyFinding:
    """Record a mitigation proposal without implying successful verification."""
    return finding.model_copy(
        update={
            "proposed_mitigation": proposed_mitigation,
            "closure_criteria": closure_criteria,
            "status": FindingStatus.MITIGATED,
        }
    )


def verify_mitigation(
    finding: SafetyFinding,
    pair: CasePair,
    *,
    agent: ReferenceAgent,
    mode: AgentMode,
    run_id: str,
) -> VerificationOutcome:
    """Rerun both CasePair conditions and apply the same evaluation semantics.

    A PASS closes the finding. FAIL keeps it open. REVIEW records unresolved
    verification and never closes the finding.
    """
    if finding.pair_id != pair.pair_id:
        raise ValueError("finding pair_id does not match CasePair")
    if finding.proposed_mitigation is None or finding.closure_criteria is None:
        raise ValueError("verification requires a recorded mitigation and closure criteria")

    constructs = required_constructs(pair)
    canonical_trace = agent.run(pair.canonical_case, run_id=f"{run_id}:canonical", mode=mode)
    perturbed_trace = agent.run(pair.perturbed_case, run_id=f"{run_id}:perturbed", mode=mode)
    canonical_results = evaluate_case(pair.canonical_case, canonical_trace, constructs)
    perturbed_results = evaluate_case(pair.perturbed_case, perturbed_trace, constructs)
    result = compare_pair(pair, canonical_results, perturbed_results)

    if result.pair_result == Verdict.PASS:
        status = FindingStatus.CLOSED
    elif result.pair_result == Verdict.REVIEW:
        status = FindingStatus.REVIEW
    else:
        status = FindingStatus.OPEN

    updated = finding.model_copy(
        update={
            "verification_run": run_id,
            "status": status,
        }
    )
    return VerificationOutcome(finding=updated, result=result)


def _failure_type(result: BehaviorDeltaResult) -> str:
    has_change_failure = any(
        check.get("label") == Verdict.FAIL or check.get("label") == Verdict.FAIL.value
        for check in result.metadata.get("checks", [])
        if check.get("reason") == "required change not satisfied"
    )
    if has_change_failure and result.invariant_violations:
        return "required_change_and_invariant_violation"
    if result.invariant_violations:
        return "invariant_violation"
    return "required_change_violation"
