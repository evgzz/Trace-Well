from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from tracewell.models import EventType, Trace, Verdict
from tracewell.semantic_judge import DecodingDeterminismClass
from tracewell.semantic_pipeline import (
    SEMANTIC_FINDING_AUTHORITY,
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
