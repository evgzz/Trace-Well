"""CasePair authoring loader for YAML/JSON sources.

See ADR-0020 and docs/ARCHITECTURE.md authoring/resolution layers.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml
from pydantic import ValidationError

from .models import CasePair


class LoadError(ValueError):
    pass


def load_case_pair(path: Path) -> CasePair:
    """Parse and validate an authored YAML or JSON CasePair."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LoadError(str(exc)) from exc

    try:
        if path.suffix.lower() == ".json":
            payload = json.loads(text)
        elif path.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(text)
        else:
            raise LoadError("CasePair source must be .json, .yaml, or .yml")
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise LoadError(str(exc)) from exc

    if not isinstance(payload, dict):
        raise LoadError("CasePair source must contain an object")
    try:
        return CasePair.model_validate(payload)
    except ValidationError as exc:
        raise LoadError(str(exc)) from exc
