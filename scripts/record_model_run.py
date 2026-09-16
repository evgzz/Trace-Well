#!/usr/bin/env python3
"""Record one TRACE-Well V1.6 real-model execution manifest.

This script is intentionally local-only and dependency-free. It hashes the exact
chat template, rendered prompt, request, and response files and writes a strict
JSON manifest for later calibration/reproduction work.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys


DECODING_CLASSES = {
    "deterministic",
    "seeded_stochastic",
    "unseeded_stochastic",
    "unknown",
}
ARTIFACT_FORMATS = {"safetensors", "gguf", "other"}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--run-id", required=True)
    value.add_argument("--model-id", required=True)
    value.add_argument("--hf-revision", required=True)
    value.add_argument("--artifact-format", required=True, choices=sorted(ARTIFACT_FORMATS))
    value.add_argument("--artifact-reference")
    value.add_argument("--weights-file", type=Path)
    value.add_argument("--quantization")
    value.add_argument("--serving-engine", required=True)
    value.add_argument("--serving-engine-version", required=True)
    value.add_argument("--endpoint", required=True)
    value.add_argument("--decoding-determinism-class", required=True, choices=sorted(DECODING_CLASSES))
    value.add_argument("--seed", type=int)
    value.add_argument("--generation-parameters", required=True, help="JSON object")
    value.add_argument("--judge-prompt-version", required=True)
    value.add_argument("--rubric-version", required=True)
    value.add_argument("--chat-template", type=Path, required=True)
    value.add_argument("--rendered-prompt", type=Path, required=True)
    value.add_argument("--request", type=Path, required=True)
    value.add_argument("--response", type=Path, required=True)
    value.add_argument("--output", type=Path, required=True)
    value.add_argument("--notes")
    return value


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def code_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    value = proc.stdout.strip()
    if len(value) != 40:
        raise RuntimeError("git HEAD is not a full 40-character SHA")
    return value


def relative_or_absolute(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(path.resolve())


def main() -> int:
    args = parser().parse_args()
    try:
        generation_parameters = json.loads(args.generation_parameters)
        if not isinstance(generation_parameters, dict):
            raise ValueError("--generation-parameters must decode to a JSON object")

        weights_digest = sha256_file(args.weights_file) if args.weights_file else None

        manifest = {
            "schema_version": "1",
            "run_id": args.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "code_sha": code_sha(),
            "model_id": args.model_id,
            "hf_revision": args.hf_revision,
            "weights_digest": weights_digest,
            "artifact_format": args.artifact_format,
            "artifact_reference": args.artifact_reference,
            "quantization": args.quantization,
            "serving_engine": args.serving_engine,
            "serving_engine_version": args.serving_engine_version,
            "endpoint": args.endpoint,
            "decoding_determinism_class": args.decoding_determinism_class,
            "seed": args.seed,
            "generation_parameters": generation_parameters,
            "judge_prompt_version": args.judge_prompt_version,
            "rubric_version": args.rubric_version,
            "chat_template_digest": sha256_file(args.chat_template),
            "rendered_prompt_digest": sha256_file(args.rendered_prompt),
            "request_digest": sha256_file(args.request),
            "response_digest": sha256_file(args.response),
            "chat_template_path": relative_or_absolute(args.chat_template),
            "rendered_prompt_path": relative_or_absolute(args.rendered_prompt),
            "request_path": relative_or_absolute(args.request),
            "response_path": relative_or_absolute(args.response),
            "notes": args.notes,
        }

        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"record_model_run error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
