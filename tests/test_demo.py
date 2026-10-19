"""Smoke-test the reviewer demo through the same CLI users run."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_offline_reviewer_demo(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo.py"), "--output-dir", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "3/3 synthetic cases matched" in result.stdout

    summaries = list(tmp_path.glob("*/demo_summary.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert summary["real_model_inference"] is False
    assert summary["statistical_validity_claimed"] is False
    assert [record["observed_verdict"] for record in summary["scenarios"]] == [
        "PASS", "FAIL", "REVIEW"
    ]
    assert [record["finding_present"] for record in summary["scenarios"]] == [
        False, True, False
    ]
    for record in summary["scenarios"]:
        evidence_dir = Path(record["evidence_dir"])
        for artifact in ("manifest.json", "result.json", "canonical_trace.json", "perturbed_trace.json"):
            assert (evidence_dir / artifact).is_file()
