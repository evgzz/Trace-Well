"""Isolated semantic-judge protocol for TRACE-Well V1.6.

The semantic judge is not ground truth. This module preserves deterministic
precedence and keeps semantic-only FAIL authority unresolved under ADR-0015.
"""

from __future__ import annotations

from enum import Enum
import json
import math
import subprocess
from typing import Any

from pydantic import Field, ValidationError, model_validator

from .models import StrictModel, Verdict


DEFAULT_JUDGE_TIMEOUT_SECONDS = 150.0


class DecodingDeterminismClass(str, Enum):
    DETERMINISTIC = "deterministic"
    SEEDED_STOCHASTIC = "seeded_stochastic"
    UNSEEDED_STOCHASTIC = "unseeded_stochastic"
    UNKNOWN = "unknown"


class JudgeProvenance(StrictModel):
    judge_id: str
    judge_version: str
    execution_mode: str
    model: str | None = None
    model_revision: str | None = None
    weights_digest: str | None = None
    inference_engine: str | None = None
    inference_engine_version: str | None = None
    quantization: str | None = None
    decoding_determinism_class: DecodingDeterminismClass
    seed: int | None = None
    generation_parameters: dict[str, Any] = Field(default_factory=dict)
    judge_prompt_version: str
    rubric_version: str
    chat_template_digest: str | None = None
    rendered_prompt_digest: str | None = None
    request_payload_digest: str | None = None


class ExpectedJudgeIdentity(StrictModel):
    """What judge artifact the caller expects to run."""

    judge_id: str | None = None
    judge_version: str | None = None
    model: str | None = None
    model_revision: str | None = None
    weights_digest: str | None = None
    judge_prompt_version: str | None = None
    rubric_version: str | None = None


class ExpectedJudgeConfiguration(StrictModel):
    """How the caller expects the judge to run."""

    execution_mode: str | None = None
    inference_engine: str | None = None
    inference_engine_version: str | None = None
    quantization: str | None = None
    decoding_determinism_class: DecodingDeterminismClass | None = None
    seed: int | None = None
    generation_parameters: dict[str, Any] | None = None
    chat_template_digest: str | None = None

    @model_validator(mode="after")
    def generation_parameters_are_standard_json(self) -> "ExpectedJudgeConfiguration":
        if self.generation_parameters is not None:
            _validate_standard_json(self.generation_parameters, path="generation_parameters")
        return self


class JudgeRequest(StrictModel):
    request_id: str
    case_id: str
    trace_id: str
    construct: str
    rubric: str
    observable_evidence: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class JudgeResponse(StrictModel):
    request_id: str
    candidate_label: Verdict
    observed_value: Any = None
    rationale: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    provenance: JudgeProvenance
    metadata: dict[str, Any] = Field(default_factory=dict)


class JudgeErrorReason(str, Enum):
    JUDGE_TIMEOUT = "JUDGE_TIMEOUT"
    JUDGE_LAUNCH_FAILED = "JUDGE_LAUNCH_FAILED"
    JUDGE_OUTPUT_NOT_UTF8 = "JUDGE_OUTPUT_NOT_UTF8"
    JUDGE_NONZERO_EXIT = "JUDGE_NONZERO_EXIT"
    JUDGE_EMPTY_OUTPUT = "JUDGE_EMPTY_OUTPUT"
    JUDGE_MALFORMED_JSON = "JUDGE_MALFORMED_JSON"
    JUDGE_SCHEMA_INVALID = "JUDGE_SCHEMA_INVALID"
    JUDGE_REQUEST_ID_MISMATCH = "JUDGE_REQUEST_ID_MISMATCH"
    INVALID_EVIDENCE_REFERENCE = "INVALID_EVIDENCE_REFERENCE"
    JUDGE_IDENTITY_MISMATCH = "JUDGE_IDENTITY_MISMATCH"
    JUDGE_CONFIGURATION_MISMATCH = "JUDGE_CONFIGURATION_MISMATCH"


class SemanticJudgeError(RuntimeError):
    default_reason: JudgeErrorReason | None = None

    def __init__(
        self,
        message: str,
        *,
        reason: JudgeErrorReason | None = None,
        rejected_response: JudgeResponse | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        resolved = reason if reason is not None else self.default_reason
        if resolved is None:
            raise TypeError(f"{type(self).__name__} requires a JudgeErrorReason")
        self.reason = JudgeErrorReason(resolved)
        self.rejected_response = rejected_response
        self.details = _json_details(details)


class SemanticJudgeTimeout(SemanticJudgeError):
    default_reason = JudgeErrorReason.JUDGE_TIMEOUT


class SemanticJudgeProtocolError(SemanticJudgeError):
    pass


class SemanticJudgeInvalidEvidenceReference(SemanticJudgeProtocolError):
    default_reason = JudgeErrorReason.INVALID_EVIDENCE_REFERENCE


class SemanticJudgeProvenanceMismatch(SemanticJudgeProtocolError):
    default_reason = JudgeErrorReason.JUDGE_IDENTITY_MISMATCH


class SemanticJudgeConfigurationMismatch(SemanticJudgeProtocolError):
    default_reason = JudgeErrorReason.JUDGE_CONFIGURATION_MISMATCH


def _json_details(details: dict[str, Any] | None) -> dict[str, Any]:
    if details is None:
        return {}
    if not isinstance(details, dict):
        raise TypeError("judge error details must be a JSON object")
    try:
        roundtrip = json.loads(json.dumps(details, allow_nan=False, sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise TypeError(f"judge error details are not JSON-serializable: {exc}") from exc
    if roundtrip != details:
        raise TypeError("judge error details must be plain JSON (str keys, lists, scalars)")
    return roundtrip


def _validate_standard_json(value: Any, *, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_standard_json(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} contains a non-string object key")
            _validate_standard_json(item, path=f"{path}.{key}")
        return
    raise ValueError(f"{path} contains unsupported non-JSON type {type(value).__name__}")


def _reject_nonstandard_constant(token: str) -> None:
    raise ValueError(f"non-standard JSON numeric constant: {token}")


def typed_json_equal(left: Any, right: Any) -> bool:
    """JSON-type-aware equality; booleans never compare equal to numbers."""
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        if not isinstance(left, (int, float)) or not isinstance(right, (int, float)):
            return False
        if isinstance(left, float) and not math.isfinite(left):
            return False
        if isinstance(right, float) and not math.isfinite(right):
            return False
        return left == right
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(typed_json_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and set(left) == set(right)
            and all(typed_json_equal(left[key], right[key]) for key in left)
        )
    return False


def request_evidence_refs(request: JudgeRequest) -> set[str]:
    refs: set[str] = set()
    for row in request.observable_evidence:
        event_id = row.get("event_id")
        if isinstance(event_id, str):
            refs.add(event_id)
        for ref in row.get("evidence_refs") or []:
            if isinstance(ref, str):
                refs.add(ref)
    return refs


def provenance_mismatches(
    expected: ExpectedJudgeIdentity,
    provenance: JudgeProvenance,
) -> dict[str, dict[str, Any]]:
    expected_values = expected.model_dump(mode="json", exclude_none=True)
    observed_values = provenance.model_dump(mode="json")
    mismatches: dict[str, dict[str, Any]] = {}
    for field, expected_value in expected_values.items():
        observed_value = observed_values[field]
        if not typed_json_equal(expected_value, observed_value):
            mismatches[field] = {"expected": expected_value, "observed": observed_value}
    return mismatches


def configuration_mismatches(
    expected: ExpectedJudgeConfiguration,
    provenance: JudgeProvenance,
) -> dict[str, dict[str, Any]]:
    expected_values = expected.model_dump(mode="json", exclude_none=True)
    observed_values = provenance.model_dump(mode="json")
    mismatches: dict[str, dict[str, Any]] = {}
    for field, expected_value in expected_values.items():
        observed_value = observed_values[field]
        if field == "generation_parameters":
            missing_or_different = False
            for key, value in expected_value.items():
                if key not in observed_value or not typed_json_equal(value, observed_value[key]):
                    missing_or_different = True
                    break
            if missing_or_different:
                mismatches[field] = {"expected": expected_value, "observed": observed_value}
        elif not typed_json_equal(expected_value, observed_value):
            mismatches[field] = {"expected": expected_value, "observed": observed_value}
    return mismatches


def run_semantic_judge(
    command: list[str],
    request: JudgeRequest,
    *,
    timeout_seconds: float = DEFAULT_JUDGE_TIMEOUT_SECONDS,
    expected_identity: ExpectedJudgeIdentity | None = None,
    expected_configuration: ExpectedJudgeConfiguration | None = None,
) -> JudgeResponse:
    payload = request.model_dump(mode="json")
    try:
        proc = subprocess.run(
            command,
            input=json.dumps(payload, ensure_ascii=False) + "\n",
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        raise SemanticJudgeTimeout(
            "semantic judge timed out", details={"timeout_seconds": timeout_seconds}
        ) from exc
    except OSError as exc:
        raise SemanticJudgeProtocolError(
            f"semantic judge failed to launch: {exc}",
            reason=JudgeErrorReason.JUDGE_LAUNCH_FAILED,
            details={"os_error": type(exc).__name__, "errno": exc.errno},
        ) from exc
    except UnicodeDecodeError as exc:
        raise SemanticJudgeProtocolError(
            "semantic judge output is not valid UTF-8",
            reason=JudgeErrorReason.JUDGE_OUTPUT_NOT_UTF8,
        ) from exc

    if proc.returncode != 0:
        raise SemanticJudgeProtocolError(
            f"semantic judge exited non-zero ({proc.returncode}): {proc.stderr.strip()}",
            reason=JudgeErrorReason.JUDGE_NONZERO_EXIT,
            details={"returncode": proc.returncode},
        )

    stdout = proc.stdout.strip()
    if not stdout:
        raise SemanticJudgeProtocolError(
            "semantic judge produced empty stdout",
            reason=JudgeErrorReason.JUDGE_EMPTY_OUTPUT,
        )

    try:
        raw = json.loads(stdout, parse_constant=_reject_nonstandard_constant)
    except (json.JSONDecodeError, ValueError) as exc:
        raise SemanticJudgeProtocolError(
            "semantic judge stdout is not valid strict JSON",
            reason=JudgeErrorReason.JUDGE_MALFORMED_JSON,
        ) from exc

    try:
        response = JudgeResponse.model_validate(raw)
    except ValidationError as exc:
        raise SemanticJudgeProtocolError(
            "semantic judge response failed schema validation",
            reason=JudgeErrorReason.JUDGE_SCHEMA_INVALID,
            details={
                "errors": [
                    {"loc": [str(part) for part in error["loc"]], "type": error["type"]}
                    for error in exc.errors()
                ]
            },
        ) from exc

    if response.request_id != request.request_id:
        raise SemanticJudgeProtocolError(
            "semantic judge response request_id mismatch",
            reason=JudgeErrorReason.JUDGE_REQUEST_ID_MISMATCH,
            rejected_response=response,
            details={"expected": request.request_id, "observed": response.request_id},
        )

    allowed_refs = request_evidence_refs(request)
    invalid_refs = [ref for ref in response.evidence_refs if ref not in allowed_refs]
    if invalid_refs:
        raise SemanticJudgeInvalidEvidenceReference(
            f"semantic judge cited evidence absent from the request: {invalid_refs}",
            rejected_response=response,
            details={"invalid_refs": invalid_refs},
        )

    identity_mismatches = (
        provenance_mismatches(expected_identity, response.provenance)
        if expected_identity is not None
        else {}
    )
    config_mismatches = (
        configuration_mismatches(expected_configuration, response.provenance)
        if expected_configuration is not None
        else {}
    )
    if identity_mismatches or config_mismatches:
        details = {**identity_mismatches, **config_mismatches}
        if identity_mismatches:
            raise SemanticJudgeProvenanceMismatch(
                f"semantic judge provenance does not match expected identity: {sorted(identity_mismatches)}",
                rejected_response=response,
                details=details,
            )
        raise SemanticJudgeConfigurationMismatch(
            f"semantic judge provenance does not match expected configuration: {sorted(config_mismatches)}",
            rejected_response=response,
            details=details,
        )

    return response


def integrate_semantic_candidate(
    *,
    deterministic_verdict: Verdict,
    specification_inconsistency: bool,
    response: JudgeResponse | None = None,
    judge_error: Exception | None = None,
) -> Verdict:
    if specification_inconsistency:
        return Verdict.REVIEW
    if deterministic_verdict == Verdict.FAIL:
        return Verdict.FAIL
    if deterministic_verdict == Verdict.REVIEW:
        return Verdict.REVIEW
    if judge_error is not None:
        return Verdict.REVIEW
    if response is None:
        return Verdict.REVIEW
    if response.candidate_label == Verdict.PASS:
        return Verdict.PASS
    return Verdict.REVIEW
