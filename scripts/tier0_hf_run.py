#!/usr/bin/env python3
"""Tier-0 hosted-endpoint run orchestration (transport_only evidence).

Uses the existing semantic pipeline and HF endpoint adapter; adds no verdict logic.

  python scripts/tier0_hf_run.py prep   # write adapter_request.json and raw_request.json
  python scripts/tier0_hf_run.py run    # execute the fixture N times and summarize

Environment: HF_TOKEN, HF_ENDPOINT_URL, HF_EXPECTED_HOST, HF_API_MODEL, HF_REVISION,
HF_ENGINE, optional HF_ENGINE_VERSION, RUN_ID. HF_ENDPOINT_URL and HF_EXPECTED_HOST
must come from scripts/tier0_admission.py; the adapter re-checks them before sending
the token.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tracewell.loader import load_case_pair  # noqa: E402
from tracewell.reference_agent import ReferenceAgent  # noqa: E402
from tracewell.runner import run_pair  # noqa: E402
from tracewell.semantic_judge import ExpectedJudgeConfiguration, ExpectedJudgeIdentity  # noqa: E402
from tracewell.semantic_pipeline import (  # noqa: E402
    build_judge_request,
    load_semantic_fixture,
    run_semantic_fixture,
)

MODEL_ID = "Qwen/Qwen2.5-0.5B-Instruct"
FIXTURE = ROOT / os.environ.get("TIER_FIXTURE", "cases/semantic/sem-001-pass.yaml")
CASES_ROOT = ROOT / "cases"
SCHEMA = os.environ.get("TIER_SCHEMA") == "1"
PROMPT_VERSION = "hf-endpoint-v1-schema" if SCHEMA else "hf-endpoint-v1"
RUBRIC_VERSION = "semantic-rubric-v1"
TEMPERATURE = 0.0
MAX_TOKENS = 256


def need(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing environment variable {name}")
    return value


def load_adapter():
    spec = importlib.util.spec_from_file_location("hf_endpoint_judge", ROOT / "scripts" / "hf_endpoint_judge.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def judge_command() -> list[str]:
    command = [
        sys.executable, str(ROOT / "scripts" / "tier0_capture_judge.py"),
        "--base-url", need("HF_ENDPOINT_URL"),
        "--expected-host", need("HF_EXPECTED_HOST"),
        "--api-model", need("HF_API_MODEL"),
        "--model", MODEL_ID,
        "--model-revision", need("HF_REVISION"),
        "--inference-engine", need("HF_ENGINE"),
        "--decoding-determinism-class", "unknown",
        "--temperature", str(TEMPERATURE),
        "--max-tokens", str(MAX_TOKENS),
        "--judge-prompt-version", PROMPT_VERSION,
        "--rubric-version", RUBRIC_VERSION,
    ]
    if os.environ.get("HF_ENGINE_VERSION"):
        command += ["--inference-engine-version", os.environ["HF_ENGINE_VERSION"]]
    if SCHEMA:
        command.append("--response-schema")
    return command


def build_request(run_id: str):
    fixture = load_semantic_fixture(FIXTURE)
    pair = load_case_pair(CASES_ROOT / fixture.pair_path)
    canonical, perturbed, _, _ = run_pair(pair, run_id=run_id, agent=ReferenceAgent(), mode=fixture.agent_mode)
    trace = canonical if fixture.condition == "canonical" else perturbed
    return build_judge_request(fixture, trace=trace, run_id=run_id)


def prep(out: Path, run_id: str) -> None:
    out.mkdir(parents=True, exist_ok=True)
    request = build_request(run_id)
    (out / "adapter_request.json").write_text(json.dumps(request.model_dump(mode="json"), indent=2) + "\n", encoding="utf-8")
    adapter = load_adapter()
    args = SimpleNamespace(api_model=need("HF_API_MODEL"), temperature=TEMPERATURE, max_tokens=MAX_TOKENS, seed=None, response_schema=SCHEMA)
    wire = adapter._encode(adapter._model_payload(request, args))
    (out / "raw_request.json").write_bytes(wire)
    print("wrote adapter_request.json and raw_request.json")
    print("raw_request.json sha256:", hashlib.sha256(wire).hexdigest())


def run(out: Path, repeats: int, prefix: str) -> None:
    identity = ExpectedJudgeIdentity(
        judge_id="tracewell.hf-inference-endpoint", model=MODEL_ID, model_revision=need("HF_REVISION"),
        judge_prompt_version=PROMPT_VERSION, rubric_version=RUBRIC_VERSION,
    )
    configuration = ExpectedJudgeConfiguration(
        execution_mode="hf_dedicated_endpoint", inference_engine=need("HF_ENGINE"),
        decoding_determinism_class="unknown",
        generation_parameters={"temperature": TEMPERATURE, "max_tokens": MAX_TOKENS},
    )
    command = judge_command()
    records = []
    for index in range(1, repeats + 1):
        run_id = f"{prefix}-r{index}"
        capture_dir = out / "captures" / run_id
        os.environ["TRACEWELL_CAPTURE_DIR"] = str(capture_dir)
        record = {"run_id": run_id}
        started = time.monotonic()
        try:
            evidence, run_dir = run_semantic_fixture(
                FIXTURE, cases_root=CASES_ROOT, output_dir=out / "runs", run_id=run_id,
                judge_command=command, expected_identity=identity, expected_configuration=configuration,
            )
            response = evidence.judge_response
            record.update(
                accepted=response is not None,
                candidate_label=response.candidate_label.value if response else None,
                integrated_verdict=evidence.integrated_verdict.value,
                deterministic_verdict=evidence.deterministic_pair_verdict.value,
                judge_error_reason=evidence.judge_error_reason.value if evidence.judge_error_reason else None,
                semantic_finding_file_present=(run_dir / "finding.json").is_file(),
                semantic_result_sha256=sha256_file(run_dir / "semantic_result.json"),
            )
        except Exception as exc:  # recorded, never repaired
            record.update(accepted=False, pipeline_exception=type(exc).__name__)
        record["wall_seconds"] = round(time.monotonic() - started, 3)
        meta_path = capture_dir / "capture_meta.json"
        if meta_path.is_file():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            record["wire_request_sha256"] = meta["wire_request_sha256"]
            record["endpoint_http_status"] = meta["http_status"]
            record["endpoint_error_type"] = meta["error_type"]
            record["endpoint_response_sha256"] = meta["response_sha256_of_reserialized_json"]
        records.append(record)
        print(json.dumps(record, sort_keys=True))
    summary = {
        "evidence_class": "transport_only",
        "attempted": len(records),
        "accepted_by_protocol": sum(1 for r in records if r.get("accepted")),
        "distinct_candidate_labels": sorted({r["candidate_label"] for r in records if r.get("candidate_label")}),
        "distinct_wire_request_digests": len({r.get("wire_request_sha256") for r in records}),
        "distinct_endpoint_response_digests": len({r.get("endpoint_response_sha256") for r in records}),
        "any_semantic_finding_file": any(r.get("semantic_finding_file_present") for r in records),
        "note": "descriptive integration observations; not judge accuracy or statistical validity",
        "runs": records,
    }
    (out / "run_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote run_summary.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=["prep", "run"])
    parser.add_argument("--run-id", default=os.environ.get("RUN_ID", "tier0-qwen-hf-001"))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--repeats", type=int, default=3)
    args = parser.parse_args()
    out = args.out or ROOT / "results" / "real-model" / args.run_id
    if args.command == "prep":
        prep(out, f"{args.run_id}-prep")
    else:
        run(out, args.repeats, args.run_id)


if __name__ == "__main__":
    main()
