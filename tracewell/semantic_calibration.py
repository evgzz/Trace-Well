"""Blinded calibration utilities for TRACE-Well V1.6 semantic judges.

Calibration evidence compares recorded judge candidate labels with independent
human/domain-expert labels keyed by opaque item IDs. It does not grant runtime
verdict or SafetyFinding authority and does not establish statistical validity.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from .models import StrictModel, Verdict


class CalibrationLabel(StrictModel):
    item_id: str
    label: Verdict


class JudgeCalibrationRecord(StrictModel):
    item_id: str
    judge_label: Verdict
    judge_id: str
    judge_version: str
    model: str | None = None
    model_revision: str | None = None
    decoding_determinism_class: str


class CalibrationPair(StrictModel):
    item_id: str
    human_label: Verdict
    judge_label: Verdict
    agreement: bool


class CalibrationReport(StrictModel):
    calibration_id: str
    total_items: int
    agreement_count: int
    disagreement_count: int
    agreement_fraction: float | None
    human_label_counts: dict[str, int] = Field(default_factory=dict)
    judge_label_counts: dict[str, int] = Field(default_factory=dict)
    confusion_counts: dict[str, int] = Field(default_factory=dict)
    pairs: list[CalibrationPair] = Field(default_factory=list)
    semantic_fail_authority_granted: Literal[False] = False
    statistical_validity_claimed: Literal[False] = False

    @model_validator(mode="after")
    def verify_counts(self) -> "CalibrationReport":
        if self.agreement_count + self.disagreement_count != self.total_items:
            raise ValueError("calibration counts do not sum to total_items")
        return self


def load_human_labels(path: Path) -> list[CalibrationLabel]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("human label file must contain a JSON array")
    labels = [CalibrationLabel.model_validate(item) for item in payload]
    _require_unique_ids([item.item_id for item in labels], "human labels")
    return labels


def load_judge_records(path: Path) -> list[JudgeCalibrationRecord]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("judge record file must contain a JSON array")
    records = [JudgeCalibrationRecord.model_validate(item) for item in payload]
    _require_unique_ids([item.item_id for item in records], "judge records")
    return records


def build_calibration_report(
    *,
    calibration_id: str,
    human_labels: list[CalibrationLabel],
    judge_records: list[JudgeCalibrationRecord],
) -> CalibrationReport:
    humans = {item.item_id: item for item in human_labels}
    judges = {item.item_id: item for item in judge_records}
    if set(humans) != set(judges):
        missing_judge = sorted(set(humans) - set(judges))
        missing_human = sorted(set(judges) - set(humans))
        raise ValueError(
            "calibration item IDs do not match; "
            f"missing judge labels={missing_judge}, missing human labels={missing_human}"
        )

    pairs: list[CalibrationPair] = []
    confusion: Counter[str] = Counter()
    human_counts: Counter[str] = Counter()
    judge_counts: Counter[str] = Counter()

    for item_id in sorted(humans):
        human = humans[item_id].label
        judge = judges[item_id].judge_label
        human_counts[human.value] += 1
        judge_counts[judge.value] += 1
        confusion[f"human={human.value}|judge={judge.value}"] += 1
        pairs.append(
            CalibrationPair(
                item_id=item_id,
                human_label=human,
                judge_label=judge,
                agreement=human == judge,
            )
        )

    agreement_count = sum(item.agreement for item in pairs)
    total = len(pairs)
    return CalibrationReport(
        calibration_id=calibration_id,
        total_items=total,
        agreement_count=agreement_count,
        disagreement_count=total - agreement_count,
        agreement_fraction=(agreement_count / total) if total else None,
        human_label_counts=dict(sorted(human_counts.items())),
        judge_label_counts=dict(sorted(judge_counts.items())),
        confusion_counts=dict(sorted(confusion.items())),
        pairs=pairs,
    )


def write_calibration_report(path: Path, report: CalibrationReport) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def _require_unique_ids(values: list[str], label: str) -> None:
    duplicates = sorted(item for item, count in Counter(values).items() if count > 1)
    if duplicates:
        raise ValueError(f"duplicate item IDs in {label}: {duplicates}")
