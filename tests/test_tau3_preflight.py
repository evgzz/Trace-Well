from __future__ import annotations

import hashlib
import json

import pytest

from tracewell.tau3_preflight import Tau3PreflightError, load_and_validate_preflight


def _hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(plan, risk):
    return {
        "plan_version": "v2",
        "provider": "example",
        "model": "example/model",
        "model_revision": "immutable-revision",
        "credential_env": "EXAMPLE_API_KEY",
        "experiment_plan_sha256": _hash(plan),
        "risk_register_sha256": _hash(risk),
        "gates": {f"G{i}": "PASS" for i in range(8)},
        "gate_evidence": {f"G{i}": f"evidence-{i}" for i in range(8)},
    }


def test_preflight_blocks_failed_gate(tmp_path):
    plan = tmp_path / "plan.md"
    risk = tmp_path / "risk.md"
    manifest_path = tmp_path / "preflight.json"
    plan.write_text("plan")
    risk.write_text("risk")
    manifest = _manifest(plan, risk)
    manifest["gates"]["G7"] = "BLOCKED"
    manifest_path.write_text(json.dumps(manifest))

    with pytest.raises(Tau3PreflightError, match="G7"):
        load_and_validate_preflight(
            manifest_path,
            experiment_plan_path=plan,
            risk_register_path=risk,
            environ={"EXAMPLE_API_KEY": "secret"},
        )


def test_preflight_blocks_missing_credential(tmp_path):
    plan = tmp_path / "plan.md"
    risk = tmp_path / "risk.md"
    manifest_path = tmp_path / "preflight.json"
    plan.write_text("plan")
    risk.write_text("risk")
    manifest_path.write_text(json.dumps(_manifest(plan, risk)))

    with pytest.raises(Tau3PreflightError, match="credential"):
        load_and_validate_preflight(
            manifest_path,
            experiment_plan_path=plan,
            risk_register_path=risk,
            environ={},
        )


def test_preflight_blocks_plan_hash_drift(tmp_path):
    plan = tmp_path / "plan.md"
    risk = tmp_path / "risk.md"
    manifest_path = tmp_path / "preflight.json"
    plan.write_text("plan")
    risk.write_text("risk")
    manifest = _manifest(plan, risk)
    manifest_path.write_text(json.dumps(manifest))
    plan.write_text("changed")

    with pytest.raises(Tau3PreflightError, match="plan hash"):
        load_and_validate_preflight(
            manifest_path,
            experiment_plan_path=plan,
            risk_register_path=risk,
            environ={"EXAMPLE_API_KEY": "secret"},
        )


def test_preflight_accepts_all_pass_frozen_manifest(tmp_path):
    plan = tmp_path / "plan.md"
    risk = tmp_path / "risk.md"
    manifest_path = tmp_path / "preflight.json"
    plan.write_text("plan")
    risk.write_text("risk")
    manifest_path.write_text(json.dumps(_manifest(plan, risk)))

    loaded = load_and_validate_preflight(
        manifest_path,
        experiment_plan_path=plan,
        risk_register_path=risk,
        environ={"EXAMPLE_API_KEY": "secret"},
    )
    assert loaded["model"] == "example/model"
    assert len(loaded["_preflight_sha256"]) == 64
