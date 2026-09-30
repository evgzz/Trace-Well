"""Executable preflight gate for the τ³ airline live experiment."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping

REQUIRED_GATES = tuple(f"G{i}" for i in range(8))


class Tau3PreflightError(ValueError):
    """Raised when live execution prerequisites are not frozen and satisfied."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_and_validate_preflight(
    path: Path,
    *,
    experiment_plan_path: Path,
    risk_register_path: Path,
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text())
    except Exception as exc:
        raise Tau3PreflightError(f"invalid preflight manifest: {exc}") from exc

    if manifest.get("plan_version") != "v2":
        raise Tau3PreflightError("preflight plan_version must be 'v2'")

    for field in ("provider", "model", "model_revision", "credential_env"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise Tau3PreflightError(f"preflight field {field!r} must be non-empty")

    gates = manifest.get("gates")
    if not isinstance(gates, dict):
        raise Tau3PreflightError("preflight gates must be an object")
    missing = [gate for gate in REQUIRED_GATES if gate not in gates]
    if missing:
        raise Tau3PreflightError(f"preflight missing gates: {missing}")
    failed = [gate for gate in REQUIRED_GATES if gates.get(gate) != "PASS"]
    if failed:
        raise Tau3PreflightError(f"live execution blocked by gates: {failed}")

    evidence = manifest.get("gate_evidence")
    if not isinstance(evidence, dict):
        raise Tau3PreflightError("preflight gate_evidence must be an object")
    missing_evidence = [
        gate
        for gate in REQUIRED_GATES
        if not isinstance(evidence.get(gate), str) or not evidence.get(gate).strip()
    ]
    if missing_evidence:
        raise Tau3PreflightError(
            f"preflight missing gate evidence: {missing_evidence}"
        )

    if manifest.get("experiment_plan_sha256") != sha256_file(experiment_plan_path):
        raise Tau3PreflightError("experiment plan hash does not match frozen v2 plan")
    if manifest.get("risk_register_sha256") != sha256_file(risk_register_path):
        raise Tau3PreflightError("risk register hash does not match current file")

    env = dict(os.environ if environ is None else environ)
    credential_env = manifest["credential_env"]
    if not env.get(credential_env):
        raise Tau3PreflightError(
            f"required provider credential environment variable {credential_env!r} is absent"
        )

    manifest["_preflight_sha256"] = sha256_file(path)
    return manifest
