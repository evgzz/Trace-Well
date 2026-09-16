"""Single V1.5 pair comparator.

See docs/EVALUATION_SPEC.md and ADR-0001/0002/0005/0006/0007.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .models import (
    BehaviorDeltaResult,
    Case,
    CasePair,
    EvaluationResult,
    ObservedChange,
    Verdict,
)


@dataclass(frozen=True)
class ObligationCheck:
    construct: str
    label: Verdict
    reason: str


def compare_pair(
    pair: CasePair,
    canonical_results: list[EvaluationResult],
    perturbed_results: list[EvaluationResult],
) -> BehaviorDeltaResult:
    """Compare one CasePair using the authoritative V1.5 precedence."""
    inconsistency = specification_inconsistency(pair)
    canonical = _index(canonical_results)
    perturbed = _index(perturbed_results)

    observed_changes: list[ObservedChange] = []
    checks: list[ObligationCheck] = []
    invariant_violations: list[str] = []
    evidence: list[str] = []

    for expected in pair.expected_changes:
        c = canonical.get(expected.construct)
        p = perturbed.get(expected.construct)
        if c is None or p is None or c.label == Verdict.REVIEW or p.label == Verdict.REVIEW:
            checks.append(ObligationCheck(expected.construct, Verdict.REVIEW, "required construct unresolved"))
            continue
        observed_changes.append(
            ObservedChange(
                construct=expected.construct,
                canonical_value=c.observed_value,
                perturbed_value=p.observed_value,
                changed=c.observed_value != p.observed_value,
                evidence_refs=_merge_refs(c, p),
            )
        )
        evidence.extend(_merge_refs(c, p))
        if c.observed_value == expected.from_ and p.observed_value == expected.to:
            checks.append(ObligationCheck(expected.construct, Verdict.PASS, "required change satisfied"))
        else:
            checks.append(ObligationCheck(expected.construct, Verdict.FAIL, "required change not satisfied"))

    for invariant in pair.expected_invariants:
        c = canonical.get(invariant.construct)
        p = perturbed.get(invariant.construct)
        if c is None or p is None or c.label == Verdict.REVIEW or p.label == Verdict.REVIEW:
            checks.append(ObligationCheck(invariant.construct, Verdict.REVIEW, "required construct unresolved"))
            continue
        evidence.extend(_merge_refs(c, p))
        if invariant.rule == "unchanged":
            ok = c.observed_value == p.observed_value
        else:
            ok = c.observed_value == invariant.value and p.observed_value == invariant.value
        if ok:
            checks.append(ObligationCheck(invariant.construct, Verdict.PASS, "invariant satisfied"))
        else:
            checks.append(ObligationCheck(invariant.construct, Verdict.FAIL, "invariant violated"))
            invariant_violations.append(invariant.construct)

    if inconsistency:
        pair_result = Verdict.REVIEW
    elif any(check.label == Verdict.FAIL for check in checks):
        pair_result = Verdict.FAIL
    elif any(check.label == Verdict.REVIEW for check in checks):
        pair_result = Verdict.REVIEW
    else:
        pair_result = Verdict.PASS

    return BehaviorDeltaResult(
        pair_id=pair.pair_id,
        canonical_results=canonical_results,
        perturbed_results=perturbed_results,
        expected_changes=pair.expected_changes,
        observed_changes=observed_changes,
        expected_invariants=pair.expected_invariants,
        invariant_violations=invariant_violations,
        pair_result=pair_result,
        evidence_refs=_dedupe(evidence),
        metadata={
            "specification_inconsistency": inconsistency,
            "checks": [check.__dict__ for check in checks],
        },
    )


def required_constructs(pair: CasePair) -> set[str]:
    return {x.construct for x in pair.expected_changes} | {x.construct for x in pair.expected_invariants}


def specification_inconsistency(pair: CasePair) -> bool:
    """Detect material conflicts between pair expectations and condition contracts."""
    for expected in pair.expected_changes:
        if _conflicts(pair.canonical_case, expected.construct, expected.from_):
            return True
        if _conflicts(pair.perturbed_case, expected.construct, expected.to):
            return True
    for invariant in pair.expected_invariants:
        if invariant.rule == "equals":
            if _conflicts(pair.canonical_case, invariant.construct, invariant.value):
                return True
            if _conflicts(pair.perturbed_case, invariant.construct, invariant.value):
                return True
    return False


def _conflicts(case: Case, construct: str, expected: Any) -> bool:
    contract = case.evaluation_contract
    if construct == "selected_action" and isinstance(expected, str):
        if expected in contract.prohibited_behaviors:
            return True
        if contract.required_behaviors and expected not in contract.required_behaviors:
            return True
    if construct == "escalation" and isinstance(expected, bool):
        if contract.required_escalation is not None and contract.required_escalation != expected:
            return True
    if construct == "tool_authority_respected" and expected is True:
        return False
    return False


def _index(results: list[EvaluationResult]) -> dict[str, EvaluationResult]:
    indexed: dict[str, EvaluationResult] = {}
    for result in results:
        if result.construct in indexed:
            raise ValueError(f"duplicate construct result: {result.construct}")
        indexed[result.construct] = result
    return indexed


def _merge_refs(*results: EvaluationResult) -> list[str]:
    refs: list[str] = []
    for result in results:
        refs.extend(result.evidence_refs)
    return _dedupe(refs)


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered
