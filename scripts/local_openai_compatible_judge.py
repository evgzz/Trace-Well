#!/usr/bin/env python3
"""Local OpenAI-compatible semantic-judge adapter for TRACE-Well V1.6.

Reads one JudgeRequest JSON object from stdin and writes one JudgeResponse JSON
object to stdout. The HTTP endpoint must be loopback-only; this adapter is for
local/open-model servers and intentionally does not support hosted endpoints.

No model SDK is required. The adapter uses only the Python standard library and
the existing TRACE-Well schema package.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from typing import Any
from urllib import error, parse, request

from tracewell.semantic_judge import (
    DecodingDeterminismClass,
    JudgeProvenance,
    JudgeRequest,
    JudgeResponse,
)
from tracewell.models import Verdict


SYSTEM_PROMPT = """You are a semantic evaluator, not ground truth.
Use only the observable evidence supplied by the request.
Do not infer or request hidden chain-of-thought.
Apply the supplied rubric to the requested construct.
If the evidence is insufficient or materially ambiguous, return REVIEW.
Return a JSON object only with these keys:
- candidate_label: PASS, FAIL, or REVIEW
- observed_value: any JSON value or null
- rationale: a concise evidence-grounded explanation, not private reasoning
- evidence_refs: an array of event_id or evidence_refs strings from the supplied evidence
"""


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8080/v1/chat/completions",
        help="Loopback OpenAI-compatible /v1/chat/completions endpoint.",
    )
    value.add_argument("--model", required=True)
    value.add_argument("--model-revision")
    value.add_argument("--weights-digest")
    value.add_argument("--inference-engine", default="openai-compatible-local")
    value.add_argument("--inference-engine-version")
    value.add_argument("--quantization")
    value.add_argument(
        "--decoding-determinism-class",
        required=True,
        choices=[item.value for item in DecodingDeterminismClass],
        help="Explicit reproducibility class; never inferred from temperature alone.",
    )
    value.add_argument("--seed", type=int)
    value.add_argument("--temperature", type=float, default=0.0)
    value.add_argument("--max-tokens", type=int, default=256)
    value.add_argument("--http-timeout-seconds", type=float, default=30.0)
    value.add_argument("--judge-version", default="1")
    value.add_argument("--judge-prompt-version", default="local-openai-compatible-v1")
    value.add_argument("--rubric-version", required=True)
    return value


def _require_loopback(endpoint: str) -> None:
    parsed = parse.urlparse(endpoint)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("endpoint scheme must be http or https")
    if parsed.hostname is None:
        raise ValueError("endpoint must include a hostname")

    hostname = parsed.hostname
    if hostname == "localhost":
        return
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError as exc:
        raise ValueError("endpoint hostname must be localhost or a loopback IP") from exc
    if not address.is_loopback:
        raise ValueError("endpoint must be loopback-only")


def _read_request() -> JudgeRequest:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("stdin did not contain a JudgeRequest")
    payload = json.loads(raw)
    return JudgeRequest.model_validate(payload)


def _model_payload(judge_request: JudgeRequest, args: argparse.Namespace) -> dict[str, Any]:
    user_payload = {
        "construct": judge_request.construct,
        "rubric": judge_request.rubric,
        "observable_evidence": judge_request.observable_evidence,
    }
    payload: dict[str, Any] = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True),
            },
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    return payload


def _post(endpoint: str, payload: dict[str, Any], timeout_seconds: float) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        endpoint,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"local judge HTTP request failed: {exc}") from exc

    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("local judge HTTP response must be a JSON object")
    return value


def _extract_content(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("OpenAI-compatible response is missing choices[0].message.content") from exc

    if isinstance(content, str):
        content = json.loads(content)
    if not isinstance(content, dict):
        raise ValueError("model message content must decode to a JSON object")
    return content


def _response(
    judge_request: JudgeRequest,
    model_output: dict[str, Any],
    args: argparse.Namespace,
) -> JudgeResponse:
    label = Verdict(model_output["candidate_label"])
    evidence_refs = model_output.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(
        isinstance(item, str) for item in evidence_refs
    ):
        raise ValueError("evidence_refs must be an array of strings")

    provenance = JudgeProvenance(
        judge_id="tracewell.local-openai-compatible",
        judge_version=args.judge_version,
        execution_mode="local_http_subprocess",
        model=args.model,
        model_revision=args.model_revision,
        weights_digest=args.weights_digest,
        inference_engine=args.inference_engine,
        inference_engine_version=args.inference_engine_version,
        quantization=args.quantization,
        decoding_determinism_class=args.decoding_determinism_class,
        seed=args.seed,
        generation_parameters={
            "temperature": args.temperature,
            "max_tokens": args.max_tokens,
        },
        judge_prompt_version=args.judge_prompt_version,
        rubric_version=args.rubric_version,
    )
    return JudgeResponse(
        request_id=judge_request.request_id,
        candidate_label=label,
        observed_value=model_output.get("observed_value"),
        rationale=model_output.get("rationale"),
        evidence_refs=evidence_refs,
        provenance=provenance,
        metadata={"adapter": "local_openai_compatible"},
    )


def main() -> int:
    args = parser().parse_args()
    try:
        _require_loopback(args.endpoint)
        judge_request = _read_request()
        http_response = _post(
            args.endpoint,
            _model_payload(judge_request, args),
            args.http_timeout_seconds,
        )
        model_output = _extract_content(http_response)
        semantic_response = _response(judge_request, model_output, args)
    except Exception as exc:  # subprocess boundary: failures surface as non-zero protocol errors
        print(f"local semantic judge adapter error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(
        json.dumps(semantic_response.model_dump(mode="json"), sort_keys=True) + "\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
