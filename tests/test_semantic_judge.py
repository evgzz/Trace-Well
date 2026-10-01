from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

from tracewell.models import Verdict
from tracewell.semantic_judge import (
    DEFAULT_JUDGE_TIMEOUT_SECONDS,
    DecodingDeterminismClass,
    ExpectedJudgeConfiguration,
    ExpectedJudgeIdentity,
    JudgeProvenance,
    json_equal,
    provenance_mismatches,
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


def request(mock_mode: str = "pass", **mock_metadata) -> JudgeRequest:
    return JudgeRequest(
        request_id="judge-req-1",
        case_id="case-1",
        trace_id="trace-1",
        construct="semantic_alignment",
        rubric="Assess the observable response against the supplied rubric.",
        observable_evidence=[{"event_id": "e1", "output": "example"}],
        metadata={"mock_mode": mock_mode, **mock_metadata},
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
        ("weights_digest", "sha256:expected-weights"),
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
    "JUDGE_CONFIGURATION_MISMATCH",
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
        update={"model": "expected-model", "weights_digest": "sha256:expected-weights"}
    )
    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(command(), request("pass"), expected_identity=expected)

    assert excinfo.value.details == {
        "model": {"expected": "expected-model", "observed": None},
        "weights_digest": {"expected": "sha256:expected-weights", "observed": None},
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



# --- ADR-0021 Amendment 1: configuration binding --------------------------------


@pytest.mark.parametrize(
    ("left", "right", "equal"),
    [
        (0, 0.0, True),
        (1, 1.0, True),
        (0.0, "0.0", False),
        (1, True, False),
        (0, False, False),
        (True, True, True),
        (None, None, True),
        (None, 0, False),
        ("a", "a", True),
        (["a", "b"], ["b", "a"], False),
        (["a", "b"], ["a", "b"], True),
        ({"a": 1}, {"a": 1.0}, True),
        ({"a": 1}, {"a": 1, "b": 2}, False),
        ({"a": [1, True]}, {"a": [1, 1]}, False),
    ],
)
def test_json_equal_is_typed(left, right, equal):
    assert json_equal(left, right) is equal
    assert json_equal(right, left) is equal


def provenance(**overrides) -> JudgeProvenance:
    values = {
        "judge_id": "j",
        "judge_version": "1",
        "execution_mode": "subprocess",
        "inference_engine": "vllm",
        "quantization": "fp16",
        "decoding_determinism_class": "deterministic",
        "generation_parameters": {"temperature": 0.0, "max_tokens": 256, "top_p": 1.0},
        "judge_prompt_version": "p1",
        "rubric_version": "r1",
    }
    values.update(overrides)
    return JudgeProvenance(**values)


def config(**fields) -> ExpectedJudgeConfiguration:
    return ExpectedJudgeConfiguration(**fields)


@pytest.mark.parametrize(
    ("expected", "returned_parameters", "mismatch"),
    [
        # subset rule: extra returned keys are unconstrained
        ({"temperature": 0.0}, {"temperature": 0.0, "max_tokens": 256, "top_p": 1.0}, None),
        ({"temperature": 0.0}, {"temperature": 0.7, "max_tokens": 256}, ({"temperature": 0.0}, {"temperature": 0.7})),
        ({"temperature": 0.0}, {"max_tokens": 256}, ({"temperature": 0.0}, {})),
        # literal null inside generation_parameters
        ({"x": None}, {"x": None}, None),
        ({"x": None}, {"x": 0}, ({"x": None}, {"x": 0})),
        ({"x": None}, {}, ({"x": None}, {})),
        # typed equality per value
        ({"temperature": 0}, {"temperature": 0.0}, None),
        ({"n": 1}, {"n": True}, ({"n": 1}, {"n": True})),
        ({"t": 0.0}, {"t": "0.0"}, ({"t": 0.0}, {"t": "0.0"})),
        # nested values use full equality, not subset
        ({"stop": ["a", "b"]}, {"stop": ["b", "a"]}, ({"stop": ["a", "b"]}, {"stop": ["b", "a"]})),
        ({"opts": {"a": 1}}, {"opts": {"a": 1, "b": 2}}, ({"opts": {"a": 1}}, {"opts": {"a": 1, "b": 2}})),
    ],
)
def test_generation_parameters_subset_matching(expected, returned_parameters, mismatch):
    result = provenance_mismatches(
        config(generation_parameters=expected),
        provenance(generation_parameters=returned_parameters),
    )
    if mismatch is None:
        assert result == {}
    else:
        assert result == {
            "generation_parameters": {"expected": mismatch[0], "observed": mismatch[1]}
        }


def test_top_level_null_is_unconstrained_and_scalars_enums_are_exact():
    observed = provenance()
    assert provenance_mismatches(config(), observed) == {}
    assert provenance_mismatches(config(quantization=None, seed=None), observed) == {}
    assert provenance_mismatches(config(quantization="int4"), observed) == {
        "quantization": {"expected": "int4", "observed": "fp16"}
    }
    assert provenance_mismatches(
        config(decoding_determinism_class=DecodingDeterminismClass.SEEDED_STOCHASTIC),
        observed,
    ) == {
        "decoding_determinism_class": {
            "expected": "seeded_stochastic",
            "observed": "deterministic",
        }
    }
    assert provenance_mismatches(config(seed=7), observed) == {
        "seed": {"expected": 7, "observed": None}
    }


def test_identity_and_configuration_cover_disjoint_provenance_fields():
    identity = set(ExpectedJudgeIdentity.model_fields)
    configuration = set(ExpectedJudgeConfiguration.model_fields)
    assert identity == {
        "judge_id", "judge_version", "model", "model_revision",
        "weights_digest", "judge_prompt_version", "rubric_version",
    }
    assert configuration == {
        "execution_mode", "inference_engine", "inference_engine_version", "quantization",
        "decoding_determinism_class", "seed", "generation_parameters", "chat_template_digest",
    }
    assert not identity & configuration
    assert (identity | configuration) <= set(JudgeProvenance.model_fields)


def test_moved_fields_are_rejected_on_identity():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        ExpectedJudgeIdentity(decoding_determinism_class="deterministic")
    with pytest.raises(ValidationError):
        ExpectedJudgeIdentity(chat_template_digest="sha256:x")


@pytest.mark.parametrize(
    "parameters",
    [
        {"t": float("nan")},
        {"t": float("inf")},
        {"t": float("-inf")},
        {"nested": {"t": [1.0, float("nan")]}},
    ],
)
def test_non_finite_expected_values_fail_validation(parameters):
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="non-finite"):
        config(generation_parameters=parameters)


def test_non_finite_returned_value_is_malformed_json_not_a_comparison():
    with pytest.raises(SemanticJudgeProtocolError) as excinfo:
        run_semantic_judge(
            command(),
            request("nonfinite"),
            expected_configuration=config(quantization="fp16"),
        )

    assert excinfo.value.reason is JudgeErrorReason.JUDGE_MALFORMED_JSON
    assert excinfo.value.rejected_response is None


def test_configuration_mismatch_end_to_end_reason_and_details():
    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(
            command(),
            request("pass", mock_generation_parameters={"temperature": 0.7}, mock_quantization="int4"),
            expected_identity=MOCK_IDENTITY,
            expected_configuration=config(
                quantization="fp16", generation_parameters={"temperature": 0.0}
            ),
        )

    error = excinfo.value
    assert error.reason is JudgeErrorReason.JUDGE_CONFIGURATION_MISMATCH
    assert error.identity_mismatches == {}
    assert error.details == {
        "quantization": {"expected": "fp16", "observed": "int4"},
        "generation_parameters": {
            "expected": {"temperature": 0.0},
            "observed": {"temperature": 0.7},
        },
    }
    assert error.rejected_response is not None


def test_dual_mismatch_identity_is_primary_and_details_cover_both():
    with pytest.raises(SemanticJudgeProvenanceMismatch) as excinfo:
        run_semantic_judge(
            command(),
            request("pass", mock_quantization="int4"),
            expected_identity=MOCK_IDENTITY.model_copy(update={"judge_version": "2"}),
            expected_configuration=config(quantization="fp16"),
        )

    error = excinfo.value
    # Primary classification only: the configuration check failed too.
    assert error.reason is JudgeErrorReason.JUDGE_IDENTITY_MISMATCH
    assert set(error.identity_mismatches) == {"judge_version"}
    assert set(error.configuration_mismatches) == {"quantization"}
    assert set(error.details) == {"judge_version", "quantization"}


def test_matching_identity_and_configuration_are_accepted():
    response = run_semantic_judge(
        command(),
        request("pass", mock_generation_parameters={"temperature": 0.0, "max_tokens": 64}),
        expected_identity=MOCK_IDENTITY,
        expected_configuration=config(
            execution_mode="subprocess",
            inference_engine="python",
            decoding_determinism_class=DecodingDeterminismClass.DETERMINISTIC,
            generation_parameters={"temperature": 0},
        ),
    )
    assert response.candidate_label == Verdict.PASS


def _raw_judge(tmp_path: Path, name: str, body: str) -> list[str]:
    """A judge that echoes a fixed raw stdout body with the request's id."""
    script = tmp_path / f"{name}.py"
    script.write_text(
        "import json, sys\n"
        "request = json.loads(sys.stdin.read())\n"
        f"sys.stdout.write({body!r}.replace('REQ', request['request_id']))\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script)]


VALID_RAW = (
    '{"request_id": "REQ", "candidate_label": "PASS", "evidence_refs": [], '
    '"provenance": {"judge_id": "j", "judge_version": "1", "execution_mode": "subprocess", '
    '"decoding_determinism_class": "deterministic", "judge_prompt_version": "p", '
    '"rubric_version": "r", "seed": SEED, "generation_parameters": {"temperature": TEMP}}}'
)


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_every_non_finite_returned_token_is_malformed_json(tmp_path: Path, token):
    judge = _raw_judge(tmp_path, "nonfinite", VALID_RAW.replace("SEED", "null").replace("TEMP", token))
    with pytest.raises(SemanticJudgeProtocolError) as excinfo:
        run_semantic_judge(judge, request(), expected_configuration=config(seed=1))
    assert excinfo.value.reason is JudgeErrorReason.JUDGE_MALFORMED_JSON


def test_finite_raw_response_parses_and_matches(tmp_path: Path):
    judge = _raw_judge(tmp_path, "finite", VALID_RAW.replace("SEED", "7").replace("TEMP", "0"))
    response = run_semantic_judge(
        judge,
        request(),
        expected_configuration=config(seed=7, generation_parameters={"temperature": 0.0}),
    )
    assert response.provenance.seed == 7


@pytest.mark.parametrize("value", [True, 1.0, "1"])
def test_seed_is_never_coerced_on_the_expected_side(value):
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        config(seed=value)


@pytest.mark.parametrize("raw_seed", ["true", "1.0", '"1"'])
def test_seed_is_never_coerced_on_the_returned_side(tmp_path: Path, raw_seed):
    judge = _raw_judge(tmp_path, "seed", VALID_RAW.replace("SEED", raw_seed).replace("TEMP", "0"))
    with pytest.raises(SemanticJudgeProtocolError) as excinfo:
        run_semantic_judge(judge, request(), expected_configuration=config(seed=1))
    # A non-integer seed is a schema failure, never a coerced MATCH.
    assert excinfo.value.reason is JudgeErrorReason.JUDGE_SCHEMA_INVALID
