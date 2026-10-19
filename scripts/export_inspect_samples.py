#!/usr/bin/env python3
"""Export a TRACE-Well CasePair as Inspect AI Sample-shaped JSONL metadata.

This is deliberately NOT an executable Inspect Task or an evaluation result.
No solver, scorer, tool policy, or paired trajectory is supplied.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path

from tracewell.loader import load_case_pair

ROOT = Path(__file__).resolve().parents[1]


def export_record(case_file: Path) -> dict:
    pair = load_case_pair(case_file)
    try:
        source = case_file.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        source = case_file.name
    return {
        "id": f"tracewell:{pair.pair_id}:{pair.version}",
        "input": (
            f"NON-EXECUTABLE TRACE-Well CasePair metadata: {pair.pair_id}. "
            "The canonical and perturbed conditions, tool policy, expected changes, "
            "and invariants are in metadata. Do not treat this as an evaluation prompt, "
            "a scored sample, or an executable agent task."
        ),
        "metadata": {
            "export_format": "inspect_sample_shape_v1",
            "execution_status": "NOT_EXECUTABLE",
            "source": source,
            "source_file_sha256": sha256(case_file.read_bytes()).hexdigest(),
            "tracewell_case_pair": pair.model_dump(mode="json", by_alias=True),
            "warning": (
                "A valid Inspect Sample-shaped record alone cannot enforce paired "
                "tool authorization or provide an Inspect Task, solver, or scorer."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Export non-executable Inspect Sample-shaped metadata")
    parser.add_argument("--case", type=Path, default=ROOT / "cases/dev/auth-001.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "results/runs/inspect-export.jsonl")
    parser.add_argument("--include-holdout", action="store_true", help="Explicitly allow holdout fixture export")
    args = parser.parse_args()
    case_path = args.case.resolve()
    if not args.include_holdout and "holdout" in case_path.parts:
        parser.error("holdout export requires --include-holdout")
    record = export_record(case_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Non-executable metadata export: {args.output}")
    print("No model execution, Inspect Task, scorer, or evaluation score created.")


if __name__ == "__main__":
    main()
