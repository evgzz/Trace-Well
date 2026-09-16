#!/usr/bin/env python3
"""Deterministic mock semantic judge for V1.6 protocol tests."""

from __future__ import annotations

import json
import sys


def main() -> int:
    raw = sys.stdin.read()
    request = json.loads(raw)

    mode = request.get("metadata", {}).get("mock_mode", "pass")
    if mode == "nonzero":
        print("mock semantic judge failure", file=sys.stderr)
        return 7
    if mode == "malformed_json":
        sys.stdout.write("{not-json}\n")
        return 0
    if mode == "schema_invalid":
        sys.stdout.write(json.dumps({"request_id": request.get("request_id")}) + "\n")
        return 0
    if mode == "request_id_mismatch":
        response_request_id = "different-request"
    else:
        response_request_id = request["request_id"]

    if mode == "fail":
        label = "FAIL"
    elif mode == "review":
        label = "REVIEW"
    else:
        label = "PASS"

    response = {
        "request_id": response_request_id,
        "candidate_label": label,
        "observed_value": {"mock_mode": mode},
        "rationale": "deterministic mock semantic judgment",
        "evidence_refs": ["mock:evidence:1"],
        "provenance": {
            "judge_id": "tracewell.mock-semantic-judge",
            "judge_version": "1",
            "execution_mode": "subprocess",
            "model": None,
            "model_revision": None,
            "weights_digest": None,
            "inference_engine": "python",
            "inference_engine_version": sys.version.split()[0],
            "quantization": None,
            "decoding_determinism_class": "deterministic",
            "seed": None,
            "generation_parameters": {},
            "judge_prompt_version": "mock-v1",
            "rubric_version": "mock-rubric-v1"
        },
        "metadata": {"mock": True}
    }
    sys.stdout.write(json.dumps(response, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
