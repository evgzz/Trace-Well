"""Benchmark inventory execution for dev and holdout CasePairs.

See docs/BENCHMARK_DESIGN.md §§14–20.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from .evidence import write_run_evidence
from .lifecycle import create_finding
from .loader import load_case_pair
from .models import Verdict
from .reference_agent import ReferenceAgent
from .runner import run_pair


@dataclass(frozen=True)
class SuiteResult:
    pair_id: str
    mode: str
    verdict: Verdict
    run_id: str
    run_dir: Path


def run_suite(
    cases_root: Path,
    *,
    output_dir: Path,
    run_prefix: str,
) -> list[SuiteResult]:
    """Run only the development inventory; holdout is intentionally excluded."""
    return _run_section(
        cases_root,
        section="dev",
        output_dir=output_dir,
        run_prefix=run_prefix,
    )


def run_holdout(
    cases_root: Path,
    *,
    output_dir: Path,
    run_prefix: str,
) -> list[SuiteResult]:
    """Run only the explicitly withheld holdout inventory."""
    return _run_section(
        cases_root,
        section="holdout",
        output_dir=output_dir,
        run_prefix=run_prefix,
    )


def _run_section(
    cases_root: Path,
    *,
    section: Literal["dev", "holdout"],
    output_dir: Path,
    run_prefix: str,
) -> list[SuiteResult]:
    inventory = _load_inventory(cases_root / "inventory.yaml")
    entries = inventory.get(section, {})
    if not isinstance(entries, dict) or not entries:
        raise ValueError(f"inventory section {section!r} is empty")

    agent = ReferenceAgent()
    outputs: list[SuiteResult] = []
    for pair_id, entry in entries.items():
        if not isinstance(entry, dict):
            raise ValueError(f"inventory entry {pair_id!r} must be an object")
        relpath = entry.get("path")
        modes = entry.get("modes")
        if not isinstance(relpath, str) or not isinstance(modes, list) or not modes:
            raise ValueError(f"inventory entry {pair_id!r} requires path and modes")

        pair = load_case_pair(cases_root / relpath)
        if pair.pair_id != pair_id:
            raise ValueError(f"inventory key {pair_id!r} does not match CasePair {pair.pair_id!r}")

        for mode in modes:
            if not isinstance(mode, str):
                raise ValueError(f"inventory mode for {pair_id!r} must be a string")
            run_id = f"{run_prefix}:{pair_id}:{mode}"
            canonical_trace, perturbed_trace, result, manifest = run_pair(
                pair,
                run_id=run_id,
                agent=agent,
                mode=mode,
            )
            finding = create_finding(pair, result)
            run_dir = write_run_evidence(
                output_dir,
                canonical_trace=canonical_trace,
                perturbed_trace=perturbed_trace,
                result=result,
                manifest=manifest,
                finding=finding,
            )
            outputs.append(
                SuiteResult(
                    pair_id=pair_id,
                    mode=mode,
                    verdict=result.pair_result,
                    run_id=run_id,
                    run_dir=run_dir,
                )
            )
    return outputs


def _load_inventory(path: Path) -> dict:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("inventory must contain an object")
    return payload
