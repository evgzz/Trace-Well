#!/usr/bin/env python3
"""Run a small offline, synthetic TRACE-Well evidence demonstration.

Uses the public CLI rather than a second evaluator implementation. No model
credentials, external service, or live agent is required.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

# (label, case, reference-agent mode, expected verdict, expected finding)
SCENARIOS = (
    ("authorized tool use", "cases/dev/auth-001.yaml", "respect_tool_boundary", "PASS", False),
    ("seeded unauthorized tool use", "cases/dev/auth-001.yaml", "violate_tool_boundary", "FAIL", True),
    ("conflicting evaluation specification", "cases/fixtures/po7-spec-inconsistent.yaml", "respect_context", "REVIEW", False),
)
REQUIRED_EVIDENCE = (
    "manifest.json",
    "canonical_trace.json",
    "perturbed_trace.json",
    "result.json",
)


def main() -> int:
    parser = argparse.ArgumentParser(description="TRACE-Well offline PASS/FAIL/REVIEW demo")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("results/runs/demo"),
        help="Evidence base directory (default: results/runs/demo, ignored by Git)",
    )
    args = parser.parse_args()

    base = args.output_dir.resolve()
    session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    session_dir = base / session_id
    session_dir.mkdir(parents=True, exist_ok=False)

    records: list[dict[str, object]] = []
    print("TRACE-Well | offline synthetic safety-evaluation demo")
    print("Scenario                              Expected  Observed  Finding")
    print("-" * 72)

    for index, (label, case_path, mode, expected, expect_finding) in enumerate(SCENARIOS, start=1):
        run_id = f"demo-{index:02d}"
        cmd = [
            sys.executable,
            "-m",
            "tracewell.cli",
            "run-pair",
            case_path,
            "--mode",
            mode,
            "--run-id",
            run_id,
            "--output-dir",
            str(session_dir),
        ]
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, check=False)
        if proc.returncode != 0:
            print(f"ERROR: {label}: CLI failed:\n{proc.stdout}\n{proc.stderr}", file=sys.stderr)
            return 1

        run_dir = session_dir / run_id
        missing = [filename for filename in REQUIRED_EVIDENCE if not (run_dir / filename).is_file()]
        if missing:
            print(f"ERROR: {label}: missing evidence: {', '.join(missing)}", file=sys.stderr)
            return 1

        try:
            result = json.loads((run_dir / "result.json").read_text(encoding="utf-8"))
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            observed = result["pair_result"]
        except (OSError, ValueError, KeyError) as exc:
            print(f"ERROR: {label}: invalid evidence: {exc}", file=sys.stderr)
            return 1

        finding_present = (run_dir / "finding.json").is_file()
        if observed != expected or finding_present != expect_finding or manifest.get("run_id") != run_id:
            print(
                f"ERROR: {label}: verdict={observed!r} expected={expected!r}; "
                f"finding={finding_present} expected={expect_finding}",
                file=sys.stderr,
            )
            return 1

        records.append({
            "scenario": label,
            "case": case_path,
            "mode": mode,
            "expected_verdict": expected,
            "observed_verdict": observed,
            "finding_present": finding_present,
            "evidence_dir": str(run_dir),
        })
        print(f"{label:<37} {expected:<9} {observed:<9} {'yes' if finding_present else 'no'}")

    summary = {
        "schema_version": "1",
        "scope": "synthetic reference-agent mechanism demonstration",
        "real_model_inference": False,
        "statistical_validity_claimed": False,
        "session_id": session_id,
        "scenarios": records,
    }
    summary_path = session_dir / "demo_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"\n3/3 synthetic cases matched expected results. Evidence: {session_dir}")
    print("No live model, semantic calibration, production safety, or generalization claim.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
