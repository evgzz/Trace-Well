#!/usr/bin/env python3
"""Hugging Face Inference Endpoints semantic-judge adapter for TRACE-Well V1.6.

This adapter targets a dedicated Hugging Face Inference Endpoint using the
OpenAI Chat Completions API. It is intentionally separate from the loopback-only
local adapter so hosted inference does not weaken the local execution boundary.

Reads one JudgeRequest JSON object from stdin and writes one JudgeResponse JSON
object to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from urllib import error, parse, request

from tracewell.models import Verdict
from tracewell.semantic_judge import (
    DecodingDeterminismClass,
    JudgeProvenance,
    JudgeRequest,
    JudgeResponse,
)


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
        "--base-url",
        required=True,
        help="Dedicated endpoint base URL, with or without trailing /v1/.",
    )
    value.add_argument("--api-model", required=True, help="Model name expected by the endpoint API.")
    value.add_argument("--model", required=True, help="Canonical Hugging Face repository id.")
    value.add_argument("--model-revision", required=True)
    value.add_argument("--weights-digest")
    value.add_argument("--inference-engine", required=True)
    value.add_argument("--inference-engine-version")
    value.add_argument("--quantization")
    value.add_argument("--chat-template-digest")
    value.add_argument("--rendered-prompt-digest")
    value.add_argument(
        "--decoding-determinism-class",
        required=True,
        choices=[item.value for item in DecodingDeterminismClass],
    )
    value.add_argument("--seed", type=int)
    value.add_argument("--temperature", type=float, default=0.0)
    value.add_argument("--max-tokens", type=int, default=256)
    value.add_argument("--http-timeout-seconds", type=float, default=120.0)
    value.add_argument("--judge-version", default="1")
    value.add_argument("--judge-prompt-version", default="hf-endpoint-v1")
    value.add_argument("--rubric-version", required=True)
    value.add_argument("--token-env", default="HF_TOKEN")
    value.add_argument(
        "--allow-http-endpoint",
        action="store_true",
        help="Testing only: allow an http endpoint. Real hosted endpoints must use https.",
    )
    return value


def _chat_url(base_url: str, *, allow_http: bool) -> str:
    parsed = parse.urlparse(base_url)
    if parsed.scheme != "https" and not (allow_http and parsed.scheme == "http"):
        raise ValueError("Hugging Face dedicated endpoint must use https")
    if not parsed.hostname:
        raise ValueError("base URL must include a hostname")

    trimmed = base_url.rstrip("/")
    if trimmed.endswith("/v1"):
        return f"{trimmed}/chat/completions"
    return f"{trimmed}/v1/chat/completions"


def _read_request() -> JudgeRequest:
    raw = sys.stdin.read()
    if not raw.strip():
        raise ValueError("stdin did not contain a JudgeRequest")
    return JudgeRequest.model_validate(json.loads(raw))


def _model_payload(judge_request: JudgeRequest, args: argparse.Namespace) -> dict[str, Any]:
    user_payload = {
        "construct": judge_request.construct,
        "rubric": judge_request.rubric,
        "observable_evidence": judge_request.observable_evidence,
    }
    payload: dict[str, Any] = {
        "model": args.api_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
    }
    if args.seed is not None:
        payload["seed"] = args.seed
    return payload


def _post(url: str, payload: dict[str, Any], *, token: str, timeout_seconds: float) -> dict[str, Any]:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    http_request = request.Request(
        url,
        data=encoded,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(http_request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8")
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(f"HF dedicated endpoint request failed: {exc}") from exc

    value = json.loads(body)
    if not isinstance(value, dict):
        raise ValueError("endpoint response must be a JSON object")
    return value


def _extract_content(response: dict[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("endpoint response is missing choices[0].message.content") from exc

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
    evidence_refs = model_output.get("evidence_refs", [])
    if not isinstance(evidence_refs, list) or not all(isinstance(item, str) for item in evidence_refs):
        raise ValueError("evidence_refs must be an array of strings")

    return JudgeResponse(
        request_id=judge_request.request_id,
        candidate_label=Verdict(model_output["candidate_label"]),
        observed_value=model_output.get("observed_value"),
        rationale=model_output.get("rationale"),
        evidence_refs=evidence_refs,
        provenance=JudgeProvenance(
            judge_id="tracewell.hf-inference-endpoint",
            judge_version=args.judge_version,
            execution_mode="hf_dedicated_endpoint",
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
            chat_template_digest=args.chat_template_digest,
            rendered_prompt_digest=args.rendered_prompt_digest,
        ),
        metadata={
            "adapter": "hf_inference_endpoint",
            "api_model": args.api_model,
        },
    )


def main() -> int:
    args = parser().parse_args()
    try:
        token = os.environ.get(args.token_env)
        if not token:
            raise ValueError(f"missing Hugging Face token in environment variable {args.token_env}")
        judge_request = _read_request()
        raw_response = _post(
            _chat_url(args.base_url, allow_http=args.allow_http_endpoint),
            _model_payload(judge_request, args),
            token=token,
            timeout_seconds=args.http_timeout_seconds,
        )
        response = _response(judge_request, _extract_content(raw_response), args)
    except Exception as exc:
        print(f"HF dedicated endpoint judge error: {exc}", file=sys.stderr)
        return 2

    sys.stdout.write(json.dumps(response.model_dump(mode="json"), sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
