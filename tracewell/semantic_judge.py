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


def run_semantic_judge(
    command: list[str],
    request: JudgeRequest,
    *,
    timeout_seconds: float = 5.0,
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
