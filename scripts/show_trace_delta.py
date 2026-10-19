#!/usr/bin/env python3
"""Summarize observable action differences in a saved TRACE-Well evidence bundle.

Reads evidence only; does not run a model or recompute the evaluator verdict.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tracewell.models import BehaviorDeltaResult, Trace
from tracewell.traces import action_events


def summarize(run_dir: Path) -> dict:
    def load(name: str) -> dict:
        return json.loads((run_dir / name).read_text(encoding="utf-8"))

    canonical = Trace.model_validate(load("canonical_trace.json"))
    perturbed = Trace.model_validate(load("perturbed_trace.json"))
    result = BehaviorDeltaResult.model_validate(load("result.json"))

    def actions(trace: Trace) -> list[dict[str, str | None]]:
        return [
            {
                "event_id": event.event_id,
                "action": action,
                "authorization_state": event.authorization_state,
            }
            for _, action, event in action_events(trace)
        ]

    finding_path = run_dir / "finding.json"
    return {
        "case_pair_id": result.pair_id,
        "canonical_actions": actions(canonical),
        "perturbed_actions": actions(perturbed),
        "invariant_violations": result.invariant_violations,
        "pair_result": result.pair_result.value,
        "finding_present": finding_path.is_file(),
        "source": "recorded synthetic or imported evidence; no re-evaluation performed",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Show observable actions and recorded paired verdict")
    parser.add_argument("run_dir", type=Path, help="One directory containing a TRACE-Well evidence bundle")
    args = parser.parse_args()
    print(json.dumps(summarize(args.run_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
