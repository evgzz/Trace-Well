from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from tracewell.models import Verdict
from tracewell.semantic_judge import (
    DEFAULT_JUDGE_TIMEOUT_SECONDS,
    DecodingDeterminismClass,
    ExpectedJudgeIdentity,
    JudgeErrorReason,
    SemanticJudgeError,
    SemanticJudgeProvenanceMismatch,
    JudgeRequest,
    SemanticJudgeInvalidEvidenceReference,
    SemanticJudgeProtocolError,
    SemanticJudgeTimeout,
    integrate_semantic_candidate,
    request_evidence_refs,
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
    assert response.evidence_refs == ["e1"]


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
        judge_error=SemanticJudgeProtocolError(
            "bad response", reason=JudgeErrorReason.JUDGE_SCHEMA_INVALID
        ),
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


def test_missing_judge_executable_is_protocol_error_and_maps_to_review(tmp_path: Path):
    with pytest.raises(SemanticJudgeProtocolError, match="failed to launch") as excinfo:
        run_semantic_judge([str(tmp_path / "missing-judge")], request("pass"))

    verdict = integrate_semantic_candidate(
        deterministic_verdict=Verdict.PASS,
        specification_inconsistency=False,
        judge_error=excinfo.value,
    )
    assert verdict == Verdict.REVIEW


def test_non_executable_judge_is_protocol_error(tmp_path: Path):
    judge = tmp_path / "not-executable-judge"
    judge.write_text("#!/bin/sh\necho '{}'\n", encoding="utf-8")
    judge.chmod(0o644)

    with pytest.raises(SemanticJudgeProtocolError, match="failed to launch"):
        run_semantic_judge([str(judge)], request("pass"))


def test_non_utf8_judge_output_is_protocol_error(tmp_path: Path):
    judge = tmp_path / "binary_judge.py"
    judge.write_text(
        "import sys\nsys.stdout.buffer.write(b'\\xff\\xfe')\n",
        encoding="utf-8",
    )

    with pytest.raises(SemanticJudgeProtocolError, match="UTF-8"):
        run_semantic_judge([sys.executable, str(judge)], request("pass"))


def test_request_evidence_refs_is_closed_set_of_event_ids_and_refs():
    judge_request = JudgeRequest(
        request_id="r",
        case_id="c",
        trace_id="t",
        construct="k",
        rubric="r",
        observable_evidence=[
            {"event_id": "e1", "evidence_refs": ["ref:a", "ref:b"]},
            {"event_id": "e2", "evidence_refs": []},
        ],
    )

    assert request_evidence_refs(judge_request) == {"e1", "e2", "ref:a", "ref:b"}


def test_fabricated_evidence_reference_is_rejected_not_discarded():
    with pytest.raises(SemanticJudgeInvalidEvidenceReference) as excinfo:
        run_semantic_judge(command(), request("fabricated_ref"))

    error = excinfo.value
    assert isinstance(error, SemanticJudgeProtocolError)
    assert error.reason == JudgeErrorReason.INVALID_EVIDENCE_REFERENCE
    assert error.details == {"invalid_refs": ["mock:fabricated:1"]}
    # The rejected response is retained for inspection, refs intact.
    assert error.rejected_response.evidence_refs == ["mock:fabricated:1"]
    assert error.rejected_response.candidate_label == Verdict.PASS


def test_fabricated_evidence_reference_cannot_preserve_pass():
    try:
        run_semantic_judge(command(), request("fabricated_ref"))
    except SemanticJudgeInvalidEvidenceReference as exc:
        verdict = integrate_semantic_candidate(
            deterministic_verdict=Verdict.PASS,
            specification_inconsistency=False,
            response=exc.rejected_response,
            judge_error=exc,
        )
    else:  # pragma: no cover - the call above must raise
        pytest.fail("fabricated evidence reference was accepted")

    assert verdict == Verdict.REVIEW



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
    assert error.reason == JudgeErrorReason.JUDGE_IDENTITY_MISMATCH
    assert list(error.details) == [field]
    assert set(error.details[field]) == {"expected", "observed"}
    assert error.rejected_response.candidate_label == Verdict.PASS


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


# --- unified rejection contract -------------------------------------------------

PINNED_REASON_CODES = {
    "JUDGE_TIMEOUT",
    "JUDGE_LAUNCH_FAILED",
    "JUDGE_OUTPUT_NOT_UTF8",
    "JUDGE_NONZERO_EXIT",
    "JUDGE_EMPTY_OUTPUT",
    "JUDGE_MALFORMED_JSON",
    "JUDGE_SCHEMA_INVALID",
    "JUDGE_REQUEST_ID_MISMATCH",
    "INVALID_EVIDENCE_REFERENCE",
    "JUDGE_IDENTITY_MISMATCH",
}


def test_reason_codes_are_stable_machine_readable_constants():
    # Changing this set is a persisted-schema change and must be deliberate.
    assert {member.value for member in JudgeErrorReason} == PINNED_REASON_CODES
    for member in JudgeErrorReason:
        assert member.value == member.name
        assert member.value.isupper() and " " not in member.value


@pytest.mark.parametrize(
    ("mock_mode", "reason", "has_rejected_response"),
    [
        ("nonzero", JudgeErrorReason.JUDGE_NONZERO_EXIT, False),
        ("malformed_json", JudgeErrorReason.JUDGE_MALFORMED_JSON, False),
        ("schema_invalid", JudgeErrorReason.JUDGE_SCHEMA_INVALID, False),
        ("request_id_mismatch", JudgeErrorReason.JUDGE_REQUEST_ID_MISMATCH, True),
        ("fabricated_ref", JudgeErrorReason.INVALID_EVIDENCE_REFERENCE, True),
    ],
)
def test_every_mock_failure_carries_reason_and_correct_rejected_response(
    mock_mode, reason, has_rejected_response
):
    with pytest.raises(SemanticJudgeError) as excinfo:
        run_semantic_judge(command(), request(mock_mode))

    error = excinfo.value
    assert error.reason is reason
    # Only a schema-valid response that the boundary rejected is preserved.
    assert (error.rejected_response is not None) is has_rejected_response
    assert json.loads(json.dumps(error.details)) == error.details


def test_failure_details_are_structured_evidence_not_exception_text(tmp_path: Path):
    with pytest.raises(SemanticJudgeError) as nonzero:
        run_semantic_judge(command(), request("nonzero"))
    assert nonzero.value.details == {"returncode": 7}

    with pytest.raises(SemanticJudgeError) as mismatch:
        run_semantic_judge(command(), request("request_id_mismatch"))
    assert mismatch.value.details == {
        "expected": "judge-req-1",
        "observed": "different-request",
    }

    with pytest.raises(SemanticJudgeError) as schema:
        run_semantic_judge(command(), request("schema_invalid"))
    assert {"loc": ["candidate_label"], "type": "missing"} in schema.value.details["errors"]

    with pytest.raises(SemanticJudgeError) as launch:
        run_semantic_judge([str(tmp_path / "missing-judge")], request("pass"))
    assert launch.value.reason is JudgeErrorReason.JUDGE_LAUNCH_FAILED
    assert launch.value.details == {"os_error": "FileNotFoundError", "errno": 2}
    assert launch.value.rejected_response is None


def test_timeout_carries_reason_and_no_rejected_response(tmp_path: Path):
    sleeper = tmp_path / "sleep_judge.py"
    sleeper.write_text("import time\ntime.sleep(0.2)\n", encoding="utf-8")

    with pytest.raises(SemanticJudgeTimeout) as excinfo:
        run_semantic_judge([sys.executable, str(sleeper)], request("pass"), timeout_seconds=0.01)

    assert excinfo.value.reason is JudgeErrorReason.JUDGE_TIMEOUT
    assert excinfo.value.rejected_response is None
    assert excinfo.value.details == {"timeout_seconds": 0.01}


def test_empty_and_non_utf8_output_reason_codes(tmp_path: Path):
    empty = tmp_path / "empty_judge.py"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SemanticJudgeProtocolError) as empty_error:
        run_semantic_judge([sys.executable, str(empty)], request("pass"))
    assert empty_error.value.reason is JudgeErrorReason.JUDGE_EMPTY_OUTPUT

    binary = tmp_path / "binary_judge.py"
    binary.write_text("import sys\nsys.stdout.buffer.write(b'\\xff\\xfe')\n", encoding="utf-8")
    with pytest.raises(SemanticJudgeProtocolError) as binary_error:
        run_semantic_judge([sys.executable, str(binary)], request("pass"))
    assert binary_error.value.reason is JudgeErrorReason.JUDGE_OUTPUT_NOT_UTF8


def test_identity_mismatch_details_use_provenance_fields_with_expected_observed():
    expected = MOCK_IDENTITY.model_copy(
        update={
            "model": "expected-model",
            "decoding_determinism_class": DecodingDeterminismClass.SEEDED_STOCHASTIC,
        }
    )
    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(command(), request("pass"), expected_identity=expected)

    assert excinfo.value.details == {
        "model": {"expected": "expected-model", "observed": None},
        "decoding_determinism_class": {
            "expected": "seeded_stochastic",
            "observed": "deterministic",
        },
    }
    assert excinfo.value.rejected_response is not None


def test_judge_error_requires_reason_code():
    with pytest.raises(TypeError, match="requires a JudgeErrorReason"):
        SemanticJudgeProtocolError("no reason given")


@pytest.mark.parametrize(
    "details",
    [
        {"value": ("tuple",)},
        {1: "non-string key"},
        {"value": float("nan")},
        {"value": object()},
        ["not", "a", "mapping"],
    ],
)
def test_judge_error_details_must_be_plain_json(details):
    with pytest.raises(TypeError):
        SemanticJudgeProtocolError(
            "bad details", reason=JudgeErrorReason.JUDGE_SCHEMA_INVALID, details=details
        )
