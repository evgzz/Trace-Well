from __future__ import annotations

import json
from pathlib import Path

import pytest

from tracewell.models import Verdict
from tracewell.semantic_calibration import (
    CalibrationLabel,
    JudgeCalibrationRecord,
    build_calibration_report,
    load_human_labels,
    load_judge_records,
    write_calibration_report,
)


def human(item_id: str, label: Verdict) -> CalibrationLabel:
    return CalibrationLabel(item_id=item_id, label=label)


def judge(item_id: str, label: Verdict) -> JudgeCalibrationRecord:
    return JudgeCalibrationRecord(
        item_id=item_id,
        judge_label=label,
        judge_id="tracewell.local-openai-compatible",
        judge_version="1",
        model="local-test-model",
        model_revision="test-rev",
        decoding_determinism_class="deterministic",
    )


def test_calibration_report_joins_by_opaque_id_and_counts_disagreement(tmp_path: Path):
    report = build_calibration_report(
        calibration_id="cal-001",
        human_labels=[
            human("item-c", Verdict.REVIEW),
            human("item-a", Verdict.PASS),
            human("item-b", Verdict.FAIL),
        ],
        judge_records=[
            judge("item-a", Verdict.PASS),
            judge("item-b", Verdict.REVIEW),
            judge("item-c", Verdict.REVIEW),
        ],
    )

    assert report.total_items == 3
    assert report.agreement_count == 2
    assert report.disagreement_count == 1
    assert report.agreement_fraction == pytest.approx(2 / 3)
    assert [item.item_id for item in report.pairs] == ["item-a", "item-b", "item-c"]
    assert report.confusion_counts == {
        "human=FAIL|judge=REVIEW": 1,
        "human=PASS|judge=PASS": 1,
        "human=REVIEW|judge=REVIEW": 1,
    }
    assert report.semantic_fail_authority_granted is False
    assert report.statistical_validity_claimed is False

    path = write_calibration_report(tmp_path / "calibration.json", report)
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["semantic_fail_authority_granted"] is False
    assert persisted["statistical_validity_claimed"] is False


def test_calibration_rejects_mismatched_item_sets():
    with pytest.raises(ValueError, match="item IDs do not match"):
        build_calibration_report(
            calibration_id="cal-mismatch",
            human_labels=[human("item-a", Verdict.PASS)],
            judge_records=[judge("item-b", Verdict.PASS)],
        )


def test_label_loaders_reject_duplicate_opaque_ids(tmp_path: Path):
    human_path = tmp_path / "human.json"
    human_path.write_text(
        json.dumps(
            [
                {"item_id": "opaque-1", "label": "PASS"},
                {"item_id": "opaque-1", "label": "FAIL"},
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate item IDs"):
        load_human_labels(human_path)

    judge_path = tmp_path / "judge.json"
    judge_path.write_text(
        json.dumps(
            [
                {
                    "item_id": "opaque-1",
                    "judge_label": "PASS",
                    "judge_id": "j",
                    "judge_version": "1",
                    "model": None,
                    "model_revision": None,
                    "decoding_determinism_class": "unknown",
                },
                {
                    "item_id": "opaque-1",
                    "judge_label": "REVIEW",
                    "judge_id": "j",
                    "judge_version": "1",
                    "model": None,
                    "model_revision": None,
                    "decoding_determinism_class": "unknown",
                },
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate item IDs"):
        load_judge_records(judge_path)
