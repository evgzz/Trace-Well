from pathlib import Path

from tracewell.models import Verdict
from tracewell.suite import run_holdout, run_suite

CASES = Path(__file__).resolve().parents[1] / "cases"


def test_dev_suite_has_distinct_pairs_and_both_directions(tmp_path: Path):
    results = run_suite(CASES, output_dir=tmp_path / "runs", run_prefix="suite-test")

    pair_ids = {item.pair_id for item in results}
    assert pair_ids == {
        "ctx-001",
        "ctx-002",
        "ctx-003",
        "unc-001",
        "unc-002",
        "auth-001",
        "auth-002",
        "late-001",
        "late-002",
    }
    assert "holdout-001" not in pair_ids
    assert len(results) == 18
    assert sum(item.verdict == Verdict.PASS for item in results) == 9
    assert sum(item.verdict == Verdict.FAIL for item in results) == 9
    assert not any(item.verdict == Verdict.REVIEW for item in results)


def test_po5_underreaction_and_overreaction_are_explicit(tmp_path: Path):
    results = run_suite(CASES, output_dir=tmp_path / "runs", run_prefix="po5")
    by_key = {(item.pair_id, item.mode): item.verdict for item in results}

    assert by_key[("ctx-001", "respect_context")] == Verdict.PASS
    assert by_key[("ctx-001", "ignore_context")] == Verdict.FAIL
    assert by_key[("ctx-001", "always_escalate")] == Verdict.FAIL


def test_po3_invariant_violation_is_pinned(tmp_path: Path):
    results = run_suite(CASES, output_dir=tmp_path / "runs", run_prefix="po3")
    by_key = {(item.pair_id, item.mode): item.verdict for item in results}

    assert by_key[("auth-002", "respect_tool_boundary")] == Verdict.PASS
    assert by_key[("auth-002", "violate_tool_boundary")] == Verdict.FAIL


def test_late_context_success_and_failure_are_pinned(tmp_path: Path):
    results = run_suite(CASES, output_dir=tmp_path / "runs", run_prefix="late")
    by_key = {(item.pair_id, item.mode): item.verdict for item in results}

    assert by_key[("late-001", "respect_late_context")] == Verdict.PASS
    assert by_key[("late-001", "ignore_late_context")] == Verdict.FAIL
    assert by_key[("late-002", "respect_late_context")] == Verdict.PASS
    assert by_key[("late-002", "ignore_late_context")] == Verdict.FAIL


def test_holdout_runs_only_through_explicit_path(tmp_path: Path):
    results = run_holdout(CASES, output_dir=tmp_path / "runs", run_prefix="holdout-test")

    assert len(results) == 1
    assert results[0].pair_id == "holdout-001"
    assert results[0].mode == "respect_context"
    assert results[0].verdict == Verdict.PASS
