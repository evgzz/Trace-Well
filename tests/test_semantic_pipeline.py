from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest
import yaml
from pydantic import ValidationError

from tracewell.models import EventType, Trace, Verdict
from tracewell.semantic_judge import DecodingDeterminismClass, ExpectedJudgeIdentity
from tracewell.semantic_pipeline import (
    SEMANTIC_FINDING_AUTHORITY,
    SemanticEvaluationEvidence,
    load_semantic_fixture,
    observable_evidence,
    run_semantic_fixture,
)
from tracewell.traces import trace_event

ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "cases"
SEMANTIC_CASES = CASES / "semantic"
MOCK = ROOT / "scripts" / "mock_semantic_judge.py"


def judge_command() -> list[str]:
    return [sys.executable, str(MOCK)]


@pytest.mark.parametrize(
    ("filename", "candidate", "integrated"),
    [
        ("sem-001-pass.yaml", Verdict.PASS, Verdict.PASS),
        ("sem-002-candidate-fail.yaml", Verdict.FAIL, Verdict.REVIEW),
        ("sem-003-review.yaml", Verdict.REVIEW, Verdict.REVIEW),
    ],
)
def test_semantic_fixture_end_to_end_persists_separate_evidence(
    tmp_path: Path,
    filename: str,
    candidate: Verdict,
    integrated: Verdict,
):
    fixture_path = SEMANTIC_CASES / filename
    fixture = load_semantic_fixture(fixture_path)

    evidence, run_dir = run_semantic_fixture(
        fixture_path,
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id=f"semantic-{fixture.fixture_id}",
        judge_command=judge_command(),
    )

    assert evidence.deterministic_pair_verdict == Verdict.PASS
    assert evidence.judge_response is not None
    assert evidence.judge_response.candidate_label == candidate
    assert evidence.integrated_verdict == integrated
    assert evidence.integrated_verdict == fixture.expected_integrated_verdict
    assert evidence.judge_response.candidate_label == fixture.expected_candidate_label
    assert evidence.semantic_finding_authority == SEMANTIC_FINDING_AUTHORITY
    assert evidence.semantic_finding_created is False
    assert (
        evidence.judge_response.provenance.decoding_determinism_class
        == DecodingDeterminismClass.DETERMINISTIC
    )

    assert (run_dir / "manifest.json").is_file()
    assert (run_dir / "canonical_trace.json").is_file()
    assert (run_dir / "perturbed_trace.json").is_file()
    assert (run_dir / "result.json").is_file()
    assert (run_dir / "semantic_result.json").is_file()

    # The underlying deterministic pair passes, so no deterministic finding is
    # created. Semantic candidate FAIL/REVIEW must not introduce one either.
    assert not (run_dir / "finding.json").exists()

    persisted = json.loads((run_dir / "semantic_result.json").read_text(encoding="utf-8"))
    assert persisted["integrated_verdict"] == integrated.value
    assert persisted["semantic_finding_authority"] == "deterministic_only"
    assert persisted["semantic_finding_created"] is False
    assert persisted["judge_response"]["candidate_label"] == candidate.value


def test_candidate_fail_is_review_and_never_creates_semantic_finding(tmp_path: Path):
    fixture_path = SEMANTIC_CASES / "sem-002-candidate-fail.yaml"

    evidence, run_dir = run_semantic_fixture(
        fixture_path,
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-candidate-fail",
        judge_command=judge_command(),
    )

    assert evidence.deterministic_pair_verdict == Verdict.PASS
    assert evidence.judge_response is not None
    assert evidence.judge_response.candidate_label == Verdict.FAIL
    assert evidence.integrated_verdict == Verdict.REVIEW
    assert evidence.semantic_finding_created is False
    assert not (run_dir / "finding.json").exists()


def test_observable_evidence_excludes_event_metadata():
    trace = Trace(
        trace_id="trace-visible-only",
        run_id="run-visible-only",
        case_id="case-visible-only",
        events=[
            trace_event(
                event_id="e1",
                event_type=EventType.AGENT_RESPONSE,
                actor="agent",
                output={"action": "continue", "text": "observable"},
                evidence_refs=["ref:1"],
                metadata={
                    "fixture_marker": "must-not-leak",
                    "hidden_control": "must-not-leak",
                },
            )
        ],
    )

    rows = observable_evidence(trace)

    assert len(rows) == 1
    assert "metadata" not in rows[0]
    assert rows[0]["event_id"] == "e1"
    assert rows[0]["output"] == {"action": "continue", "text": "observable"}
    assert "must-not-leak" not in json.dumps(rows)


def _fixture_with_mock_mode(tmp_path: Path, mock_mode: str) -> Path:
    payload = yaml.safe_load((SEMANTIC_CASES / "sem-001-pass.yaml").read_text(encoding="utf-8"))
    payload["fixture_id"] = f"sem-test-{mock_mode}"
    payload["judge_metadata"] = {"mock_mode": mock_mode}
    payload["expected_integrated_verdict"] = "REVIEW"
    path = tmp_path / f"{mock_mode}.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return path


DETERMINISTIC_FILES = (
    "manifest.json",
    "canonical_trace.json",
    "perturbed_trace.json",
    "result.json",
)


def test_judge_launch_failure_is_review_with_complete_evidence_package(tmp_path: Path):
    evidence, run_dir = run_semantic_fixture(
        SEMANTIC_CASES / "sem-001-pass.yaml",
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-launch-failure",
        judge_command=[str(tmp_path / "missing-judge")],
    )

    assert evidence.deterministic_pair_verdict == Verdict.PASS
    assert evidence.judge_response is None
    assert evidence.judge_error_type == "SemanticJudgeProtocolError"
    assert evidence.integrated_verdict == Verdict.REVIEW
    for name in (*DETERMINISTIC_FILES, "semantic_result.json"):
        assert (run_dir / name).is_file()

    persisted = json.loads((run_dir / "semantic_result.json").read_text(encoding="utf-8"))
    assert persisted["integrated_verdict"] == "REVIEW"
    assert "failed to launch" in persisted["judge_error_message"]


def test_fabricated_evidence_reference_is_review_and_persisted(tmp_path: Path):
    evidence, run_dir = run_semantic_fixture(
        _fixture_with_mock_mode(tmp_path, "fabricated_ref"),
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-fabricated-ref",
        judge_command=judge_command(),
    )

    assert evidence.deterministic_pair_verdict == Verdict.PASS
    assert evidence.integrated_verdict == Verdict.REVIEW
    # Never accepted as a semantic candidate...
    assert evidence.judge_response is None
    assert evidence.judge_error_type == "SemanticJudgeInvalidEvidenceReference"
    assert evidence.judge_error_reason == "INVALID_EVIDENCE_REFERENCE"
    # ...but not silently discarded either.
    assert evidence.rejected_judge_response is not None
    assert evidence.rejected_judge_response.evidence_refs == ["mock:fabricated:1"]
    assert not (run_dir / "finding.json").exists()

    persisted = json.loads((run_dir / "semantic_result.json").read_text(encoding="utf-8"))
    assert persisted["judge_error_reason"] == "INVALID_EVIDENCE_REFERENCE"
    assert persisted["rejected_judge_response"]["evidence_refs"] == ["mock:fabricated:1"]
    assert persisted["judge_response"] is None


def test_accepted_judge_refs_are_drawn_from_request_evidence(tmp_path: Path):
    evidence, _ = run_semantic_fixture(
        SEMANTIC_CASES / "sem-001-pass.yaml",
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-valid-refs",
        judge_command=judge_command(),
    )

    assert evidence.judge_response is not None
    assert evidence.judge_response.evidence_refs
    allowed = {row["event_id"] for row in evidence.judge_request.observable_evidence}
    for row in evidence.judge_request.observable_evidence:
        allowed.update(row["evidence_refs"])
    assert set(evidence.judge_response.evidence_refs) <= allowed
    assert evidence.judge_error_reason is None
    assert evidence.rejected_judge_response is None


def test_rejected_and_accepted_judge_responses_cannot_coexist(tmp_path: Path):
    evidence, _ = run_semantic_fixture(
        _fixture_with_mock_mode(tmp_path, "fabricated_ref"),
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-exclusive",
        judge_command=judge_command(),
    )
    payload = evidence.model_dump(mode="json")
    rejected = payload["rejected_judge_response"]

    both = {**payload, "judge_response": rejected}
    with pytest.raises(ValidationError, match="both an accepted and a rejected"):
        SemanticEvaluationEvidence.model_validate(both)

    accepted_with_error = {**payload, "judge_response": rejected, "rejected_judge_response": None}
    with pytest.raises(ValidationError, match="cannot coexist with a judge error"):
        SemanticEvaluationEvidence.model_validate(accepted_with_error)

    rejected_without_reason = {**payload, "judge_error_reason": None}
    with pytest.raises(ValidationError, match="requires a judge_error_reason"):
        SemanticEvaluationEvidence.model_validate(rejected_without_reason)



def test_judge_identity_mismatch_is_review_with_complete_evidence_package(tmp_path: Path):
    evidence, run_dir = run_semantic_fixture(
        SEMANTIC_CASES / "sem-001-pass.yaml",
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id="semantic-identity-mismatch",
        judge_command=judge_command(),
        expected_identity=ExpectedJudgeIdentity(judge_id="tracewell.expected-judge"),
    )

    assert evidence.deterministic_pair_verdict == Verdict.PASS
    assert evidence.judge_response is None
    assert evidence.judge_error_type == "SemanticJudgeProvenanceMismatch"
    assert "judge_id" in evidence.judge_error_message
    assert evidence.integrated_verdict == Verdict.REVIEW
    assert (run_dir / "semantic_result.json").is_file()


# --- unified rejection contract, end to end -------------------------------------


def _run(tmp_path: Path, run_id: str, **kwargs):
    kwargs.setdefault("judge_command", judge_command())
    fixture = kwargs.pop("fixture", SEMANTIC_CASES / "sem-001-pass.yaml")
    return run_semantic_fixture(
        fixture,
        cases_root=CASES,
        output_dir=tmp_path / "runs",
        run_id=run_id,
        **kwargs,
    )


def _persisted(run_dir: Path) -> dict:
    return json.loads((run_dir / "semantic_result.json").read_text(encoding="utf-8"))


def _assert_rejection(evidence, run_dir, *, reason: str, has_rejected_response: bool):
    persisted = _persisted(run_dir)
    assert evidence.integrated_verdict == Verdict.REVIEW
    assert evidence.judge_response is None
    assert persisted["judge_response"] is None
    assert persisted["integrated_verdict"] == "REVIEW"
    assert persisted["judge_error_reason"] == reason
    assert (persisted["rejected_judge_response"] is not None) is has_rejected_response
    assert isinstance(persisted["judge_error_details"], dict)
    # The persisted record is plain JSON and re-validates to the same evidence.
    assert SemanticEvaluationEvidence.model_validate(persisted) == evidence
    assert not (run_dir / "finding.json").exists()
    return persisted


def test_identity_mismatch_preserves_rejected_response_like_invalid_evidence(tmp_path: Path):
    evidence, run_dir = _run(
        tmp_path,
        "rejection-identity",
        expected_identity=ExpectedJudgeIdentity(judge_id="tracewell.expected-judge"),
    )
    persisted = _assert_rejection(
        evidence, run_dir, reason="JUDGE_IDENTITY_MISMATCH", has_rejected_response=True
    )
    assert persisted["judge_error_details"] == {
        "judge_id": {
            "expected": "tracewell.expected-judge",
            "observed": "tracewell.mock-semantic-judge",
        }
    }
    assert persisted["rejected_judge_response"]["provenance"]["judge_id"] == (
        "tracewell.mock-semantic-judge"
    )


def test_invalid_evidence_reference_uses_generic_rejection_path(tmp_path: Path):
    evidence, run_dir = _run(
        tmp_path,
        "rejection-invalid-ref",
        fixture=_fixture_with_mock_mode(tmp_path, "fabricated_ref"),
    )
    persisted = _assert_rejection(
        evidence, run_dir, reason="INVALID_EVIDENCE_REFERENCE", has_rejected_response=True
    )
    assert persisted["judge_error_details"] == {"invalid_refs": ["mock:fabricated:1"]}


@pytest.mark.parametrize(
    ("mock_mode", "reason"),
    [
        ("nonzero", "JUDGE_NONZERO_EXIT"),
        ("malformed_json", "JUDGE_MALFORMED_JSON"),
        ("schema_invalid", "JUDGE_SCHEMA_INVALID"),
    ],
)
def test_pre_response_failures_have_no_rejected_response(tmp_path: Path, mock_mode, reason):
    evidence, run_dir = _run(
        tmp_path,
        f"rejection-{mock_mode}",
        fixture=_fixture_with_mock_mode(tmp_path, mock_mode),
    )
    _assert_rejection(evidence, run_dir, reason=reason, has_rejected_response=False)


def test_launch_failure_and_timeout_have_no_rejected_response(tmp_path: Path):
    evidence, run_dir = _run(
        tmp_path,
        "rejection-launch",
        judge_command=[str(tmp_path / "missing-judge")],
    )
    _assert_rejection(evidence, run_dir, reason="JUDGE_LAUNCH_FAILED", has_rejected_response=False)

    sleeper = tmp_path / "sleep_judge.py"
    sleeper.write_text("import time\ntime.sleep(0.5)\n", encoding="utf-8")
    evidence, run_dir = _run(
        tmp_path,
        "rejection-timeout",
        judge_command=[sys.executable, str(sleeper)],
        timeout_seconds=0.05,
    )
    persisted = _assert_rejection(
        evidence, run_dir, reason="JUDGE_TIMEOUT", has_rejected_response=False
    )
    assert persisted["judge_error_details"] == {"timeout_seconds": 0.05}


def test_rejection_details_are_deterministic_across_runs(tmp_path: Path):
    expected_identity = ExpectedJudgeIdentity(judge_id="tracewell.expected-judge")
    first, first_dir = _run(tmp_path, "determinism-1", expected_identity=expected_identity)
    second, second_dir = _run(tmp_path, "determinism-2", expected_identity=expected_identity)

    for key in ("judge_error_reason", "judge_error_details"):
        assert _persisted(first_dir)[key] == _persisted(second_dir)[key]


def test_accepted_response_has_no_error_fields(tmp_path: Path):
    evidence, run_dir = _run(tmp_path, "accepted")
    persisted = _persisted(run_dir)

    assert evidence.judge_response is not None
    for key in (
        "judge_error_type",
        "judge_error_message",
        "judge_error_reason",
        "judge_error_details",
        "rejected_judge_response",
    ):
        assert persisted[key] is None


def test_judge_error_without_reason_code_is_schema_invalid(tmp_path: Path):
    evidence, _ = _run(
        tmp_path,
        "reason-required",
        fixture=_fixture_with_mock_mode(tmp_path, "nonzero"),
    )
    payload = evidence.model_dump(mode="json")
    with pytest.raises(ValidationError, match="requires a judge_error_reason code"):
        SemanticEvaluationEvidence.model_validate({**payload, "judge_error_reason": None})
    with pytest.raises(ValidationError):
        SemanticEvaluationEvidence.model_validate({**payload, "judge_error_reason": "free text"})
