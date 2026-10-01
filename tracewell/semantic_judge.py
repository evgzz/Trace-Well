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

from pydantic import Field, StrictInt, ValidationError, field_validator

from .models import StrictModel, Verdict


# Subprocess budget for one judge execution. It must exceed the HTTP timeouts
# of the bundled adapters (local: 30s, hosted endpoint: 120s) plus interpreter
# startup, so a slow-but-healthy hosted judge is not killed by the caller.
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
    seed: StrictInt | None = None  # no bool/float/str coercion (typed equality)
    generation_parameters: dict[str, Any] = Field(default_factory=dict)
    judge_prompt_version: str
    rubric_version: str
    chat_template_digest: str | None = None
    rendered_prompt_digest: str | None = None
    request_payload_digest: str | None = None


class ExpectedJudgeIdentity(StrictModel):
    """What judge artifact must have run (ADR-0021 Amendment 1).

    A null field is unconstrained; every non-null field must match exactly.
    """

    judge_id: str | None = None
    judge_version: str | None = None
    model: str | None = None
    model_revision: str | None = None
    weights_digest: str | None = None
    judge_prompt_version: str | None = None
    rubric_version: str | None = None


class ExpectedJudgeConfiguration(StrictModel):
    """How the judge must have run (ADR-0021 Amendment 1).

    A null top-level field is unconstrained. ``generation_parameters`` is
    matched as a subset: every expected key must be returned with an equal
    value, and an expected value of ``None`` constrains that key to JSON null.
    """

    execution_mode: str | None = None
    inference_engine: str | None = None
    inference_engine_version: str | None = None
    quantization: str | None = None
    decoding_determinism_class: DecodingDeterminismClass | None = None
    seed: StrictInt | None = None  # no bool/float/str coercion (typed equality)
    generation_parameters: dict[str, Any] | None = None
    chat_template_digest: str | None = None

    @field_validator("generation_parameters")
    @classmethod
    def _standard_json_only(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        if value is not None:
            require_standard_json(value, path="generation_parameters")
        return value


IDENTITY_FIELDS = tuple(ExpectedJudgeIdentity.model_fields)
CONFIGURATION_FIELDS = tuple(ExpectedJudgeConfiguration.model_fields)
assert not set(IDENTITY_FIELDS) & set(CONFIGURATION_FIELDS)


def require_standard_json(value: Any, *, path: str = "$") -> None:
    """Reject anything that is not a standard, finite JSON value."""
    if value is None or isinstance(value, (bool, str)):
        return
    if isinstance(value, int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: non-finite number is not a valid JSON value")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            require_standard_json(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path}: object keys must be strings")
            require_standard_json(item, path=f"{path}.{key}")
        return
    raise ValueError(f"{path}: {type(value).__name__} is not a JSON value")


def json_equal(left: Any, right: Any) -> bool:
    """Typed equality over JSON values (ADR-0021 Amendment 1).

    Values of different JSON types are never equal, so ``1 != True`` and
    ``0.0 != "0.0"``; numbers compare by value (``0 == 0.0``); arrays are
    ordered; objects need the same key set and equal values.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        return (
            isinstance(left, (int, float))
            and isinstance(right, (int, float))
            and left == right
        )
    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(json_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(
            json_equal(left[key], right[key]) for key in left
        )
    return False


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
    """Stable machine-readable codes for every semantic-judge rejection."""

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
    """Base error for isolated judge execution failures.

    Every judge error carries one rejection contract:

    - ``reason``: a stable ``JudgeErrorReason`` code; prose stays in the message;
    - ``rejected_response``: the schema-valid response the boundary rejected,
      or ``None`` when the failure occurred before one existed;
    - ``details``: JSON-serializable structured evidence, never exception text.
    """

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
    """A schema-valid response cited evidence absent from the request."""

    default_reason = JudgeErrorReason.INVALID_EVIDENCE_REFERENCE


class SemanticJudgeProvenanceMismatch(SemanticJudgeProtocolError):
    """Returned provenance does not match the expected identity and/or configuration.

    ``reason`` is only the primary classification (identity wins when both
    fail); the per-check mismatch maps say which comparisons actually failed.
    """

    def __init__(
        self,
        message: str,
        *,
        rejected_response: JudgeResponse,
        identity_mismatches: dict[str, dict[str, Any]],
        configuration_mismatches: dict[str, dict[str, Any]],
    ) -> None:
        if not identity_mismatches and not configuration_mismatches:
            raise ValueError("a provenance mismatch requires at least one mismatched field")
        super().__init__(
            message,
            reason=(
                JudgeErrorReason.JUDGE_IDENTITY_MISMATCH
                if identity_mismatches
                else JudgeErrorReason.JUDGE_CONFIGURATION_MISMATCH
            ),
            rejected_response=rejected_response,
            details={**identity_mismatches, **configuration_mismatches},
        )
        self.identity_mismatches = identity_mismatches
        self.configuration_mismatches = configuration_mismatches


def _json_details(details: dict[str, Any] | None) -> dict[str, Any]:
    """Require details to survive a strict JSON round-trip unchanged."""
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


def request_evidence_refs(request: JudgeRequest) -> set[str]:
    """Return the closed set of references a judge response may cite."""
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
    expected: ExpectedJudgeIdentity | ExpectedJudgeConfiguration,
    provenance: JudgeProvenance,
) -> dict[str, dict[str, Any]]:
    """Return {field: {expected, observed}} for every constrained field that differs.

    Null top-level expectation fields are unconstrained. ``generation_parameters``
    is compared as a subset; an expected key that is absent from the returned
    parameters is reported with ``observed`` omitted from that key's entry.
    """
    mismatches: dict[str, dict[str, Any]] = {}
    for field in type(expected).model_fields:
        expected_value = _plain(getattr(expected, field))
        if expected_value is None:
            continue
        observed_value = _plain(getattr(provenance, field))
        if field == "generation_parameters":
            differing = _generation_parameter_mismatches(expected_value, observed_value or {})
            if differing:
                mismatches[field] = {
                    "expected": {key: expected_value[key] for key in differing},
                    "observed": {
                        key: observed_value[key]
                        for key in differing
                        if key in (observed_value or {})
                    },
                }
        elif not json_equal(expected_value, observed_value):
            mismatches[field] = {"expected": expected_value, "observed": observed_value}
    return mismatches


def _generation_parameter_mismatches(
    expected: dict[str, Any],
    observed: dict[str, Any],
) -> list[str]:
    return sorted(
        key
        for key, value in expected.items()
        if key not in observed or not json_equal(value, observed[key])
    )


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def _reject_non_standard_constant(token: str) -> Any:
    raise ValueError(f"non-standard JSON constant {token!r}")


def run_semantic_judge(
    command: list[str],
    request: JudgeRequest,
    *,
    timeout_seconds: float = DEFAULT_JUDGE_TIMEOUT_SECONDS,
    expected_identity: ExpectedJudgeIdentity | None = None,
    expected_configuration: ExpectedJudgeConfiguration | None = None,
) -> JudgeResponse:
    """Execute one semantic judge request through a strict subprocess boundary."""
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
            "semantic judge timed out",
            details={"timeout_seconds": timeout_seconds},
        ) from exc
    except OSError as exc:
        # Missing executable, permission denied, or other launch failure.
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
        # Strict JSON: NaN/Infinity/-Infinity are invalid protocol values.
        raw = json.loads(stdout, parse_constant=_reject_non_standard_constant)
    except ValueError as exc:
        raise SemanticJudgeProtocolError(
            "semantic judge stdout is not valid JSON",
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

    # From here on the response is schema-valid; any rejection preserves it.
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

    # Both comparisons always run so each check's outcome is known (ADR-0021).
    identity_mismatches = (
        provenance_mismatches(expected_identity, response.provenance)
        if expected_identity is not None
        else {}
    )
    configuration_mismatches = (
        provenance_mismatches(expected_configuration, response.provenance)
        if expected_configuration is not None
        else {}
    )
    if identity_mismatches or configuration_mismatches:
        raise SemanticJudgeProvenanceMismatch(
            "semantic judge provenance does not match expectation: "
            f"{sorted({**identity_mismatches, **configuration_mismatches})}",
            rejected_response=response,
            identity_mismatches=identity_mismatches,
            configuration_mismatches=configuration_mismatches,
        )

    return response


def integrate_semantic_candidate(
    *,
    deterministic_verdict: Verdict,
    specification_inconsistency: bool,
    response: JudgeResponse | None = None,
    judge_error: Exception | None = None,
) -> Verdict:
    """Integrate a semantic candidate without granting semantic-only FAIL authority.

    Precedence for V1.6 milestone 1:
      global spec inconsistency -> REVIEW
      deterministic FAIL -> FAIL
      unresolved deterministic REVIEW -> REVIEW
      judge execution/protocol uncertainty -> REVIEW
      semantic PASS -> PASS
      semantic FAIL -> REVIEW pending ADR-0015
      semantic REVIEW -> REVIEW
    """
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
