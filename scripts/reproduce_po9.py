#!/usr/bin/env python3
"""Execute the tracked PO-9 reproduction procedure and write a machine-readable report.

This script is suitable for a clean CI runner or a third-party checkout. It
proves the deterministic clean-environment procedure, but it does not claim to
be a separate human/operator attestation.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        list(args),
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"command failed ({proc.returncode}): {' '.join(args)}\n"
            f"stdout:\n{proc.stdout}\n"
            f"stderr:\n{proc.stderr}"
        )
    return proc


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AssertionError(f"expected JSON object: {path}")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def command_summary(proc: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def parse_suite(stdout: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=3)
        if len(parts) != 4:
            raise AssertionError(f"unexpected suite output line: {line!r}")
        pair_id, mode, verdict, run_dir = parts
        rows.append(
            {
                "pair_id": pair_id,
                "mode": mode,
                "verdict": verdict,
                "run_dir": run_dir,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "results" / "reproduction",
    )
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    commit_proc = run("git", "rev-parse", "HEAD")
    commit = commit_proc.stdout.strip()

    pytest_proc = run(sys.executable, "-m", "pytest", "-q")
    scan_proc = run(sys.executable, "scripts/check_public_text.py")

    pass_proc = run(
        "tracewell",
        "run-pair",
        "cases/dev/auth-001.yaml",
        "--mode",
        "respect_tool_boundary",
        "--run-id",
        "repro-auth-pass",
        "--output-dir",
        str(runs_dir),
    )
    pass_result = load_json(runs_dir / "repro-auth-pass" / "result.json")
    pass_manifest = load_json(runs_dir / "repro-auth-pass" / "manifest.json")
    require(pass_result["pair_result"] == "PASS", "expected deterministic PASS")

    fail_proc = run(
        "tracewell",
        "run-pair",
        "cases/dev/auth-001.yaml",
        "--mode",
        "violate_tool_boundary",
        "--run-id",
        "repro-auth-fail",
        "--output-dir",
        str(runs_dir),
    )
    fail_result = load_json(runs_dir / "repro-auth-fail" / "result.json")
    fail_manifest = load_json(runs_dir / "repro-auth-fail" / "manifest.json")
    require(fail_result["pair_result"] == "FAIL", "expected deterministic FAIL")
    require(
        (runs_dir / "repro-auth-fail" / "finding.json").is_file(),
        "FAIL run must persist finding.json",
    )

    require(
        pass_manifest["artifact_digest"] == fail_manifest["artifact_digest"],
        "mode-only change must preserve CasePair artifact_digest",
    )
    require(
        pass_manifest["agent_mode"] == "respect_tool_boundary",
        "PASS manifest agent_mode mismatch",
    )
    require(
        fail_manifest["agent_mode"] == "violate_tool_boundary",
        "FAIL manifest agent_mode mismatch",
    )
    require(
        pass_manifest["execution_source"] == "agent_runner"
        and fail_manifest["execution_source"] == "agent_runner",
        "built-in runs must record execution_source=agent_runner",
    )

    review_proc = run(
        "tracewell",
        "run-pair",
        "cases/fixtures/po7-spec-inconsistent.yaml",
        "--mode",
        "respect_context",
        "--run-id",
        "repro-po7-review",
        "--output-dir",
        str(runs_dir),
    )
    review_result = load_json(runs_dir / "repro-po7-review" / "result.json")
    require(review_result["pair_result"] == "REVIEW", "expected global REVIEW")
    require(
        review_result.get("metadata", {}).get("specification_inconsistency") is True,
        "REVIEW must record specification inconsistency",
    )
    require(
        not (runs_dir / "repro-po7-review" / "finding.json").exists(),
        "REVIEW must not create a normal SafetyFinding",
    )

    suite_proc = run(
        "tracewell",
        "run-suite",
        "--cases-root",
        "cases",
        "--run-prefix",
        "repro-suite",
        "--output-dir",
        str(runs_dir),
    )
    suite_rows = parse_suite(suite_proc.stdout)
    suite_pair_ids = {row["pair_id"] for row in suite_rows}
    suite_counts = {
        "PASS": sum(row["verdict"] == "PASS" for row in suite_rows),
        "FAIL": sum(row["verdict"] == "FAIL" for row in suite_rows),
        "REVIEW": sum(row["verdict"] == "REVIEW" for row in suite_rows),
    }
    require(len(suite_pair_ids) == 9, "expected 9 distinct development CasePairs")
    require(len(suite_rows) == 18, "expected 18 deterministic development executions")
    require(suite_counts == {"PASS": 9, "FAIL": 9, "REVIEW": 0}, "suite verdict counts mismatch")
    require("holdout-001" not in suite_pair_ids, "run-suite must exclude holdout")

    holdout_proc = run(
        "tracewell",
        "run-holdout",
        "--cases-root",
        "cases",
        "--run-prefix",
        "repro-holdout",
        "--output-dir",
        str(runs_dir),
    )
    holdout_rows = parse_suite(holdout_proc.stdout)
    require(len(holdout_rows) == 1, "expected exactly one holdout execution")
    require(holdout_rows[0]["pair_id"] == "holdout-001", "unexpected holdout pair")
    require(holdout_rows[0]["verdict"] == "PASS", "expected holdout PASS")

    report = {
        "repository_commit": commit,
        "execution_environment": {
            "python": sys.version.splitlines()[0],
            "platform": platform.platform(),
            "ci": os.environ.get("CI") == "true",
            "github_actions": os.environ.get("GITHUB_ACTIONS") == "true",
        },
        "operator_class": "automated_clean_runner",
        "independent_human_operator_signoff": False,
        "gates": {
            "pytest": command_summary(pytest_proc),
            "public_text_scan": command_summary(scan_proc),
        },
        "pass_reproduction": {
            "verdict": pass_result["pair_result"],
            "manifest": pass_manifest,
            "command": command_summary(pass_proc),
        },
        "fail_reproduction": {
            "verdict": fail_result["pair_result"],
            "finding_present": True,
            "manifest": fail_manifest,
            "command": command_summary(fail_proc),
        },
        "review_reproduction": {
            "verdict": review_result["pair_result"],
            "specification_inconsistency": True,
            "finding_present": False,
            "command": command_summary(review_proc),
        },
        "artifact_run_separation": {
            "artifact_digest_match": pass_manifest["artifact_digest"] == fail_manifest["artifact_digest"],
            "artifact_digest": pass_manifest["artifact_digest"],
            "pass_agent_mode": pass_manifest["agent_mode"],
            "fail_agent_mode": fail_manifest["agent_mode"],
        },
        "development_suite": {
            "distinct_casepairs": len(suite_pair_ids),
            "executions": len(suite_rows),
            "verdict_counts": suite_counts,
        },
        "holdout": {
            "distinct_casepairs": 1,
            "verdict": holdout_rows[0]["verdict"],
        },
        "unexpected_deviations": [],
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "po9-reproduction-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"PO-9 clean-runner reproduction passed: {report_path}")
    print("Independent human/operator signoff remains intentionally open.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
