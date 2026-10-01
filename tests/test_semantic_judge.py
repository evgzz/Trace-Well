from __future__ import annotations

from pathlib import Path
import sys

import pytest

from tracewell.models import Verdict
from tracewell.semantic_judge import (
    DEFAULT_JUDGE_TIMEOUT_SECONDS,
    DecodingDeterminismClass,
    ExpectedJudgeIdentity,
    SemanticJudgeProvenanceMismatch,
    JudgeRequest,
    SemanticJudgeProtocolError,
    SemanticJudgeTimeout,
    integrate_semantic_candidate,
    run_semantic_judge,
)

ROOT = Path(__file__).resolve().parents[1]
MOCK = ROOT / "scripts" / "mock_semantic_judge.py"


def request(mock_mode: str = "pass") -> JudgeRequest:
    return JudgeRequest(
        request_id="judge-req-1",
        case_id="case-1",
        trace_id="trace-1",
        construct="semantic_alignment",
        rubric="Assess the observable response against the supplied rubric.",
        observable_evidence=[{"event_id": "e1", "output": "example"}],
        metadata={"mock_mode": mock_mode},
    )


def command() -> list[str]:
    return [sys.executable, str(MOCK)]


def test_mock_judge_returns_strict_response_with_determinism_class():
    response = run_semantic_judge(command(), request("pass"))

    assert response.candidate_label == Verdict.PASS
    assert response.provenance.decoding_determinism_class == DecodingDeterminismClass.DETERMINISTIC
    assert response.provenance.judge_id == "tracewell.mock-semantic-judge"
    assert response.request_id == "judge-req-1"


def test_semantic_only_fail_does_not_gain_final_fail_authority():
    response = run_semantic_judge(command(), request("fail"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        response=response,
    )

    assert response.candidate_label == Verdict.FAIL
    assert verdict == Verdict.REVIEW


def test_semantic_pass_can_preserve_pass_when_deterministic_path_is_clear():
    response = run_semantic_judge(command(), request("pass"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        response=response,
    )

    assert verdict == Verdict.PASS


def test_global_specification_inconsistency_outranks_deterministic_fail():
    response = run_semantic_judge(command(), request("pass"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.FAIL,
        specification_inconsistency=True,
        response=response,
    )

    assert verdict == Verdict.REVIEW


def test_deterministic_fail_cannot_be_erased_by_semantic_pass():
    response = run_semantic_judge(command(), request("pass"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.FAIL,
        specification_inconsistency=False,
        response=response,
    )

    assert verdict == Verdict.FAIL


def test_deterministic_review_remains_review():
    response = run_semantic_judge(command(), request("pass"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.REVIEW,
        specification_inconsistency=False,
        response=response,
    )

    assert verdict == Verdict.REVIEW


def test_judge_review_remains_review():
    response = run_semantic_judge(command(), request("review"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        response=response,
    )

    assert verdict == Verdict.REVIEW


def test_nonzero_exit_is_protocol_error():
    with pytest.raises(SemanticJudgeProtocolError, match="exited non-zero"):
        run_semantic_judge(command(), request("nonzero"))


def test_malformed_json_is_protocol_error():
    with pytest.raises(SemanticJudgeProtocolError, match="not valid JSON"):
        run_semantic_judge(command(), request("malformed_json"))


def test_schema_invalid_response_is_protocol_error():
    with pytest.raises(SemanticJudgeProtocolError, match="schema validation"):
        run_semantic_judge(command(), request("schema_invalid"))


def test_request_id_mismatch_is_protocol_error():
    with pytest.raises(SemanticJudgeProtocolError, match="request_id mismatch"):
        run_semantic_judge(command(), request("request_id_mismatch"))


def test_judge_error_maps_to_review():
    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        judge_error=SemanticJudgeProtocolError("bad response"),
    )

    assert verdict == Verdict.REVIEW


def test_timeout_maps_to_review_and_timeout_type_is_distinct(tmp_path: Path):
    sleeper = tmp_path / "sleep_judge.py"
    sleeper.write_text(
        "import time\n"
        "time.sleep(0.2)\n"
        "print('{}')\n",
        encoding="utf-8",
    )

    with pytest.raises(SemanticJudgeTimeout):
        run_semantic_judge(
            [sys.executable, str(sleeper)],
            request("pass"),
            timeout_seconds=0.01,
        )


MOCK_IDENTITY = ExpectedJudgeIdentity(
    judge_id="tracewell.mock-semantic-judge",
    judge_version="1",
    decoding_determinism_class=DecodingDeterminismClass.DETERMINISTIC,
    judge_prompt_version="mock-v1",
    rubric_version="mock-rubric-v1",
)


def test_matching_expected_identity_is_accepted():
    response = run_semantic_judge(command(), request("pass"), expected_identity=MOCK_IDENTITY)

    assert response.candidate_label == Verdict.PASS


@pytest.mark.parametrize(
    ("field", "expected_value"),
    [
        ("judge_id", "tracewell.some-other-judge"),
        ("judge_version", "2"),
        ("model", "expected-model"),
        ("decoding_determinism_class", DecodingDeterminismClass.SEEDED_STOCHASTIC),
        ("rubric_version", "rubric-v2"),
    ],
)
def test_provenance_identity_mismatch_is_protocol_error(field, expected_value):
    expected = MOCK_IDENTITY.model_copy(update={field: expected_value})

    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(command(), request("pass"), expected_identity=expected)

    error = excinfo.value
    assert isinstance(error, SemanticJudgeProtocolError)
    assert error.reason == "JUDGE_IDENTITY_MISMATCH"
    assert list(error.mismatches) == [field]
    assert error.response.candidate_label == Verdict.PASS


def test_provenance_identity_mismatch_cannot_preserve_pass():
    expected = MOCK_IDENTITY.model_copy(update={"model_revision": "pinned-rev"})
    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(command(), request("pass"), expected_identity=expected)

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        judge_error=excinfo.value,
    )
    assert verdict == Verdict.REVIEW


def test_default_judge_timeout_exceeds_bundled_adapter_http_timeouts():
    import importlib.util

    for name in ("local_openai_compatible_judge", "hf_endpoint_judge"):
        spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        http_timeout = module.parser().get_default("http_timeout_seconds")
        assert DEFAULT_JUDGE_TIMEOUT_SECONDS > http_timeout, name
