"""Inspect metadata export and recorded trace-difference smoke tests."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from tracewell.loader import load_case_pair
from tracewell.reference_agent import ReferenceAgent
from tracewell.runner import run_pair
from tracewell.evidence import write_run_evidence
from tracewell.lifecycle import create_finding

ROOT = Path(__file__).resolve().parents[1]


def test_inspect_export_round_trips_complete_pair(tmp_path: Path) -> None:
    out = tmp_path / "inspect.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/export_inspect_samples.py"),
         "--case", str(ROOT / "cases/dev/auth-001.yaml"), "--output", str(out)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    record = json.loads(out.read_text(encoding="utf-8").strip())
    assert record["id"] == "tracewell:auth-001:1"
    assert "target" not in record
    assert record["metadata"]["execution_status"] == "NOT_EXECUTABLE"
    pair = load_case_pair(ROOT / "cases/dev/auth-001.yaml")
    assert record["metadata"]["tracewell_case_pair"] == pair.model_dump(mode="json", by_alias=True)
    assert record["metadata"]["tracewell_case_pair"]["expected_changes"][0]["from"] == "execute_action"
    assert len(record["metadata"]["source_file_sha256"]) == 64


def test_holdout_not_exported_without_opt_in(tmp_path: Path) -> None:
    out = tmp_path / "inspect.jsonl"
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/export_inspect_samples.py"),
         "--case", str(ROOT / "cases/holdout/holdout-001.yaml"), "--output", str(out)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    assert not out.exists()


def test_recorded_unauthorized_tool_diff(tmp_path: Path) -> None:
    pair = load_case_pair(ROOT / "cases/dev/auth-001.yaml")
    c, p, verdict, manifest = run_pair(
        pair, run_id="inspect-trace-test",
        agent=ReferenceAgent(), mode="violate_tool_boundary",
    )
    assert verdict.pair_result.value == "FAIL"
    run_dir = write_run_evidence(
        tmp_path, canonical_trace=c, perturbed_trace=p,
        result=verdict, manifest=manifest, finding=create_finding(pair, verdict),
    )
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/show_trace_delta.py"), str(run_dir)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    obj = json.loads(result.stdout)
    assert obj["pair_result"] == "FAIL"
    assert obj["canonical_actions"][-1]["authorization_state"] == "allowed"
    assert obj["perturbed_actions"][-1]["authorization_state"] == "prohibited"
    assert "tool_authority_respected" in obj["invariant_violations"]
    assert obj["finding_present"] is True
