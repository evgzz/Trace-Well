"""File-based evidence persistence for deterministic V1.5 runs.

See docs/ARCHITECTURE.md persistence section and docs/REPRODUCIBILITY.md.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from .models import BehaviorDeltaResult, RunManifest, SafetyFinding, Trace


def write_run_evidence(
    output_dir: Path,
    *,
    canonical_trace: Trace,
    perturbed_trace: Trace,
    result: BehaviorDeltaResult,
    manifest: RunManifest,
    finding: SafetyFinding | None = None,
) -> Path:
    """Persist one inspectable run bundle and return its directory."""
    run_dir = output_dir / manifest.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_json(run_dir / "canonical_trace.json", canonical_trace)
    _write_json(run_dir / "perturbed_trace.json", perturbed_trace)
    _write_json(run_dir / "result.json", result)
    _write_json(run_dir / "manifest.json", manifest)
    if finding is not None:
        _write_json(run_dir / "finding.json", finding)
    return run_dir


def _write_json(path: Path, value: BaseModel) -> None:
    payload = value.model_dump(mode="json", by_alias=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
