"""End-to-end semantic fixture execution for TRACE-Well V1.6.

This module is additive to the frozen V1.5 evaluator/comparator. It builds a
JudgeRequest from observable trace fields, executes an isolated semantic judge,
applies conservative milestone-1 integration, and persists semantic evidence.

Milestone-1 finding authority is deliberately deterministic-only: semantic
judge output cannot create or close a SafetyFinding while ADR-0015 remains
Proposed.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field

from .evidence import write_run_evidence
from .lifecycle import create_finding
from .loader import load_case_pair
from .models import StrictModel, Trace, Verdict
from .reference_agent import ReferenceAgent
from .runner import run_pair
from .semantic_judge import (
    JudgeRequest,
    JudgeResponse,
    SemanticJudgeError,
    integrate_semantic_candidate,
    run_semantic_judge,
)


SEMANTIC_FINDING_AUTHORITY = "deterministic_only"


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
    integrated_verdict: Verdict
    semantic_finding_authority: Literal["deterministic_only"] = "deterministic_only"
    semantic_finding_created: Literal[False] = False


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
    timeout_seconds: float = 5.0,
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
        )
    except SemanticJudgeError as exc:
        judge_error = exc

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
        integrated_verdict=integrated,
    )

    _write_json(run_dir / "semantic_result.json", evidence)
    return evidence, run_dir


def _write_json(path: Path, value: StrictModel) -> None:
    path.write_text(
        json.dumps(value.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
