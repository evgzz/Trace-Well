"""Isolated semantic-judge protocol for TRACE-Well V1.6.

The semantic judge is not ground truth. This module preserves deterministic
precedence and keeps semantic-only FAIL authority unresolved under ADR-0015.
"""

from __future__ import annotations

from enum import Enum
import json
import subprocess
from typing import Any

from pydantic import Field, ValidationError

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
    seed: int | None = None
    generation_parameters: dict[str, Any] = Field(default_factory=dict)
    judge_prompt_version: str
    rubric_version: str
    chat_template_digest: str | None = None
    rendered_prompt_digest: str | None = None
    request_payload_digest: str | None = None


class ExpectedJudgeIdentity(StrictModel):
    """Judge identity the caller configured; each non-null field must match."""

    judge_id: str | None = None
    judge_version: str | None = None
    model: str | None = None
    model_revision: str | None = None
    decoding_determinism_class: DecodingDeterminismClass | None = None
    judge_prompt_version: str | None = None
    rubric_version: str | None = None
    chat_template_digest: str | None = None


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


class SemanticJudgeError(RuntimeError):
    """Base error for isolated judge execution failures."""


class SemanticJudgeTimeout(SemanticJudgeError):
    pass


class SemanticJudgeProtocolError(SemanticJudgeError):
    pass


class SemanticJudgeProvenanceMismatch(SemanticJudgeProtocolError):
    """Returned provenance does not identify the judge the caller configured."""

    reason = "JUDGE_IDENTITY_MISMATCH"

    def __init__(
        self,
        message: str,
        *,
        response: JudgeResponse,
        mismatches: dict[str, dict[str, Any]],
    ) -> None:
        super().__init__(message)
        self.response = response
        self.mismatches = mismatches


def provenance_mismatches(
    expected: ExpectedJudgeIdentity,
    provenance: JudgeProvenance,
) -> dict[str, dict[str, Any]]:
    """Return {field: {expected, returned}} for every configured field that differs."""
    mismatches: dict[str, dict[str, Any]] = {}
    for field, expected_value in expected.model_dump(exclude_none=True).items():
        returned_value = getattr(provenance, field)
        if returned_value != expected_value:
            mismatches[field] = {
                "expected": _plain(expected_value),
                "returned": _plain(returned_value),
            }
    return mismatches


def _plain(value: Any) -> Any:
    return value.value if isinstance(value, Enum) else value


def run_semantic_judge(
    command: list[str],
    request: JudgeRequest,
    *,
    timeout_seconds: float = DEFAULT_JUDGE_TIMEOUT_SECONDS,
    expected_identity: ExpectedJudgeIdentity | None = None,
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
        raise SemanticJudgeTimeout("semantic judge timed out") from exc

    if proc.returncode != 0:
        raise SemanticJudgeProtocolError(
            f"semantic judge exited non-zero ({proc.returncode}): {proc.stderr.strip()}"
        )

    stdout = proc.stdout.strip()
    if not stdout:
        raise SemanticJudgeProtocolError("semantic judge produced empty stdout")

    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise SemanticJudgeProtocolError("semantic judge stdout is not valid JSON") from exc

    try:
        response = JudgeResponse.model_validate(raw)
    except ValidationError as exc:
        raise SemanticJudgeProtocolError("semantic judge response failed schema validation") from exc

    if response.request_id != request.request_id:
        raise SemanticJudgeProtocolError("semantic judge response request_id mismatch")

    if expected_identity is not None:
        mismatches = provenance_mismatches(expected_identity, response.provenance)
        if mismatches:
            raise SemanticJudgeProvenanceMismatch(
                f"semantic judge provenance does not match expected identity: {sorted(mismatches)}",
                response=response,
                mismatches=mismatches,
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
