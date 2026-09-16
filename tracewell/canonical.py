"""Canonical artifact normalization and identity.

See ADR-0020 and docs/REPRODUCIBILITY.md.
"""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from pydantic import BaseModel

CANONICALIZATION_VERSION = "1"


class CanonicalizationError(ValueError):
    """Raised when an object cannot safely participate in artifact identity."""


def _reject_identity_floats(value: Any, path: str = "$") -> None:
    if isinstance(value, float):
        raise CanonicalizationError(
            f"unconstrained float not allowed in identity-bearing artifact at {path}"
        )
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_identity_floats(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_identity_floats(child, f"{path}[{index}]")


def _strip_nonsemantic_metadata(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_nonsemantic_metadata(child)
            for key, child in value.items()
            if key != "metadata"
        }
    if isinstance(value, list):
        return [_strip_nonsemantic_metadata(child) for child in value]
    return value


def _to_python(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json", by_alias=True, exclude_none=False)
    if isinstance(value, dict):
        return value
    raise TypeError("canonical artifacts must be a Pydantic model or mapping")


def canonical_payload(value: BaseModel | dict[str, Any]) -> dict[str, Any]:
    """Return the effective identity-bearing payload.

    Free-form `metadata` keys are excluded recursively by V1.5 design.
    """

    payload = _strip_nonsemantic_metadata(_to_python(value))
    _reject_identity_floats(payload)
    return payload


def canonical_json(value: BaseModel | dict[str, Any]) -> str:
    payload = canonical_payload(value)
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def artifact_digest(value: BaseModel | dict[str, Any]) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return sha256(encoded).hexdigest()
