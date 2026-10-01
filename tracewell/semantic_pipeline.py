"""End-to-end semantic fixture execution for TRACE-Well V1.6.

This module is additive to the frozen V1.5 evaluator/comparator. It builds a
JudgeRequest from observable trace fields, executes an isolated semantic judge,
applies conservative milestone-1 integration, and persists semantic evidence.

Milestone-1 finding authority is deliberately deterministic-only: semantic
judge output cannot create or close a SafetyFinding while ADR-0015 remains
Proposed.
"""

from __future__ import annotations

from enum import Enum
import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, model_validator

from .evidence import write_run_evidence
from .lifecycle import create_finding
from .loader import load_case_pair
from .models import StrictModel, Trace, Verdict
from .reference_agent import ReferenceAgent
from .runner import run_pair
from .semantic_judge import (
    DEFAULT_JUDGE_TIMEOUT_SECONDS,
    CONFIGURATION_FIELDS,
    IDENTITY_FIELDS,
    ExpectedJudgeConfiguration,
    ExpectedJudgeIdentity,
    JudgeErrorReason,
    JudgeRequest,
    JudgeResponse,
    SemanticJudgeError,
    SemanticJudgeProvenanceMismatch,
    integrate_semantic_candidate,
    run_semantic_judge,
)


SEMANTIC_FINDING_AUTHORITY = "deterministic_only"


class JudgeBindingCheck(str, Enum):
    """Outcome of comparing returned provenance with one caller expectation."""

    NOT_REQUESTED = "NOT_REQUESTED"  # caller supplied no expectation
    MATCH = "MATCH"  # compared; every constrained field matched
    MISMATCH = "MISMATCH"  # compared; at least one field differed
    NOT_EVALUATED = "NOT_EVALUATED"  # requested, but the judge failed before comparison


PROVENANCE_MISMATCH_REASONS = frozenset(
    {
        JudgeErrorReason.JUDGE_IDENTITY_MISMATCH,
        JudgeErrorReason.JUDGE_CONFIGURATION_MISMATCH,
    }
)


class SemanticFixture(StrictModel):
    fixture_id: str
    family: str
    pair_path: str
    agent_mode: str
    condition: Literal["canonical", "perturbed"]
    construct: str
    rubric: str
    judge_metadata: dict[str, Any] = Field(default_factory=dict)
    expected_candidate_label: Verdict
    expected_integrated_verdict: Verdict


class SemanticEvaluationEvidence(StrictModel):
    semantic_run_id: str
    fixture_id: str
    family: str
    pair_id: str
    case_id: str
    condition: Literal["canonical", "perturbed"]
    construct: str
    deterministic_pair_verdict: Verdict
    specification_inconsistency: bool
    judge_request: JudgeRequest
    judge_response: JudgeResponse | None = None
    judge_error_type: str | None = None
    judge_error_message: str | None = None
    judge_error_reason: JudgeErrorReason | None = None
    judge_error_details: dict[str, Any] | None = None
    # A schema-valid response rejected by the protocol boundary (for example,
    # fabricated evidence references or an identity mismatch). Persisted for
    # inspection only; it never contributes a semantic candidate.
    rejected_judge_response: JudgeResponse | None = None
    expected_judge_identity: ExpectedJudgeIdentity | None = None
    judge_identity_check: JudgeBindingCheck
    expected_judge_configuration: ExpectedJudgeConfiguration | None = None
    judge_configuration_check: JudgeBindingCheck
    integrated_verdict: Verdict
    semantic_finding_authority: Literal["deterministic_only"] = "deterministic_only"
    semantic_finding_created: Literal[False] = False

    @model_validator(mode="after")
    def accepted_and_rejected_are_exclusive(self) -> "SemanticEvaluationEvidence":
        if self.judge_response is not None and self.rejected_judge_response is not None:
            raise ValueError("an attempt cannot have both an accepted and a rejected judge response")
        if self.judge_response is not None and self.judge_error_type is not None:
            raise ValueError("an accepted judge response cannot coexist with a judge error")
        if self.rejected_judge_response is not None and self.judge_error_reason is None:
            raise ValueError("a rejected judge response requires a judge_error_reason")
        if self.judge_error_reason is not None and self.judge_error_type is None:
            raise ValueError("judge_error_reason requires judge_error_type")
        if self.judge_error_type is not None and self.judge_error_reason is None:
            raise ValueError("every judge error requires a judge_error_reason code")
        if self.judge_error_details is not None and self.judge_error_type is None:
            raise ValueError("judge_error_details requires judge_error_type")
        return self

    @model_validator(mode="after")
    def binding_checks_are_consistent(self) -> "SemanticEvaluationEvidence":
        reason = self.judge_error_reason
        compared = self.judge_response is not None or reason in PROVENANCE_MISMATCH_REASONS
        details = self.judge_error_details or {}
        for name, expected, check, fields in (
            ("identity", self.expected_judge_identity, self.judge_identity_check, IDENTITY_FIELDS),
            (
                "configuration",
                self.expected_judge_configuration,
                self.judge_configuration_check,
                CONFIGURATION_FIELDS,
            ),
        ):
            if (check == JudgeBindingCheck.NOT_REQUESTED) != (expected is None):
                raise ValueError(f"{name}: NOT_REQUESTED iff no expectation was supplied")
            if expected is None:
                continue
            if compared == (check == JudgeBindingCheck.NOT_EVALUATED):
                raise ValueError(
                    f"{name}: NOT_EVALUATED iff the judge failed before comparison"
                )
            has_field_evidence = any(field in details for field in fields)
            if compared and (check == JudgeBindingCheck.MISMATCH) != has_field_evidence:
                raise ValueError(
                    f"{name}: MISMATCH iff judge_error_details contains {name} fields"
                )
        identity_failed = self.judge_identity_check == JudgeBindingCheck.MISMATCH
        configuration_failed = self.judge_configuration_check == JudgeBindingCheck.MISMATCH
        if reason == JudgeErrorReason.JUDGE_IDENTITY_MISMATCH and not identity_failed:
            raise ValueError("JUDGE_IDENTITY_MISMATCH requires identity check MISMATCH")
        if reason == JudgeErrorReason.JUDGE_CONFIGURATION_MISMATCH and (
            identity_failed or not configuration_failed
        ):
            raise ValueError(
                "JUDGE_CONFIGURATION_MISMATCH requires configuration MISMATCH and "
                "no identity MISMATCH (identity is the primary reason)"
            )
        if (identity_failed or configuration_failed) and reason not in PROVENANCE_MISMATCH_REASONS:
            raise ValueError("a MISMATCH check requires a provenance-mismatch reason")
        return self


def load_semantic_fixture(path: Path) -> SemanticFixture:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("semantic fixture must contain an object")
    return SemanticFixture.model_validate(payload)


def observable_evidence(trace: Trace) -> list[dict[str, Any]]:
    """Project a trace to an explicit observable allowlist.

    Event metadata is intentionally excluded so fixture controls, hidden state,
    or future non-observable annotations cannot leak into semantic judgment.
    """
    rows: list[dict[str, Any]] = []
    for event in trace.events:
        rows.append(
            {
                "event_id": event.event_id,
                "event_type": event.event_type.value,
                "actor": event.actor,
                "input": event.input,
                "output": event.output,
                "tool": event.tool,
                "tool_arguments": event.tool_arguments,
                "tool_result": event.tool_result,
                "authorization_state": event.authorization_state,
                "evidence_refs": list(event.evidence_refs),
            }
        )
    return rows


def build_judge_request(
    fixture: SemanticFixture,
    *,
    trace: Trace,
    run_id: str,
) -> JudgeRequest:
    return JudgeRequest(
        request_id=f"{run_id}:judge",
        case_id=trace.case_id,
        trace_id=trace.trace_id,
        construct=fixture.construct,
        rubric=fixture.rubric,
        observable_evidence=observable_evidence(trace),
        metadata={
            "fixture_id": fixture.fixture_id,
            **fixture.judge_metadata,
        },
    )


def run_semantic_fixture(
    fixture_path: Path,
    *,
    cases_root: Path,
    output_dir: Path,
    run_id: str,
    judge_command: list[str],
    timeout_seconds: float = DEFAULT_JUDGE_TIMEOUT_SECONDS,
    expected_identity: ExpectedJudgeIdentity | None = None,
    expected_configuration: ExpectedJudgeConfiguration | None = None,
) -> tuple[SemanticEvaluationEvidence, Path]:
    """Execute one semantic fixture and persist deterministic + semantic evidence.

    SafetyFinding creation is based only on the frozen deterministic V1.5
    result. Semantic candidate labels are persisted separately and cannot create
    findings during milestone 1.
    """
    fixture = load_semantic_fixture(fixture_path)
    pair = load_case_pair(cases_root / fixture.pair_path)

    canonical_trace, perturbed_trace, deterministic_result, manifest = run_pair(
        pair,
        run_id=run_id,
        agent=ReferenceAgent(),
        mode=fixture.agent_mode,
    )

    # Deliberately evaluated before semantic execution: milestone-1 findings are
    # deterministic-only and semantic output cannot create or close them.
    deterministic_finding = create_finding(pair, deterministic_result)
    run_dir = write_run_evidence(
        output_dir,
        canonical_trace=canonical_trace,
        perturbed_trace=perturbed_trace,
        result=deterministic_result,
        manifest=manifest,
        finding=deterministic_finding,
    )

    trace = canonical_trace if fixture.condition == "canonical" else perturbed_trace
    request = build_judge_request(fixture, trace=trace, run_id=run_id)
    spec_inconsistency = bool(
        deterministic_result.metadata.get("specification_inconsistency", False)
    )

    response: JudgeResponse | None = None
    judge_error: SemanticJudgeError | None = None
    try:
        response = run_semantic_judge(
            judge_command,
            request,
            timeout_seconds=timeout_seconds,
            expected_identity=expected_identity,
            expected_configuration=expected_configuration,
        )
    except SemanticJudgeError as exc:
        judge_error = exc

    identity_check = _binding_check(expected_identity, response, judge_error, "identity")
    configuration_check = _binding_check(
        expected_configuration, response, judge_error, "configuration"
    )

    integrated = integrate_semantic_candidate(
        deterministic_verdict=deterministic_result.pair_result,
        specification_inconsistency=spec_inconsistency,
        response=response,
        judge_error=judge_error,
    )

    # Defense-in-depth against accidental future semantic-only FAIL authority.
    if integrated == Verdict.FAIL and deterministic_result.pair_result != Verdict.FAIL:
        raise RuntimeError(
            "semantic-only FAIL authority is disabled while ADR-0015 remains Proposed"
        )

    evidence = SemanticEvaluationEvidence(
        semantic_run_id=run_id,
        fixture_id=fixture.fixture_id,
        family=fixture.family,
        pair_id=pair.pair_id,
        case_id=trace.case_id,
        condition=fixture.condition,
        construct=fixture.construct,
        deterministic_pair_verdict=deterministic_result.pair_result,
        specification_inconsistency=spec_inconsistency,
        judge_request=request,
        judge_response=response,
        judge_error_type=type(judge_error).__name__ if judge_error is not None else None,
        judge_error_message=str(judge_error) if judge_error is not None else None,
        judge_error_reason=judge_error.reason if judge_error is not None else None,
        judge_error_details=judge_error.details if judge_error is not None else None,
        rejected_judge_response=judge_error.rejected_response if judge_error is not None else None,
        expected_judge_identity=expected_identity,
        judge_identity_check=identity_check,
        expected_judge_configuration=expected_configuration,
        judge_configuration_check=configuration_check,
        integrated_verdict=integrated,
    )

    _write_json(run_dir / "semantic_result.json", evidence)
    return evidence, run_dir


def _binding_check(
    expected: ExpectedJudgeIdentity | ExpectedJudgeConfiguration | None,
    response: JudgeResponse | None,
    judge_error: SemanticJudgeError | None,
    name: str,
) -> JudgeBindingCheck:
    if expected is None:
        return JudgeBindingCheck.NOT_REQUESTED
    if response is not None:
        # run_semantic_judge only returns a response after every comparison matched.
        return JudgeBindingCheck.MATCH
    if isinstance(judge_error, SemanticJudgeProvenanceMismatch):
        # Both comparisons ran; report each independently of the primary reason.
        failed = getattr(judge_error, f"{name}_mismatches")
        return JudgeBindingCheck.MISMATCH if failed else JudgeBindingCheck.MATCH
    return JudgeBindingCheck.NOT_EVALUATED


def _write_json(path: Path, value: StrictModel) -> None:
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
