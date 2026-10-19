#!/usr/bin/env python3
"""Tier-0 capture wrapper: runs scripts/hf_endpoint_judge.py unchanged.

Additionally saves the exact wire request bytes and the parsed endpoint response
for each call into $TRACEWELL_CAPTURE_DIR. No retries, no output repair.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location("hf_endpoint_judge", ROOT / "scripts" / "hf_endpoint_judge.py")
adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adapter)
_original_post = adapter._post


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _save(directory: Path, encoded: bytes, parsed, error, status, seconds: float) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "wire_request.json").write_bytes(encoded)
    meta = {
        "wire_request_sha256": _sha(encoded),
        "duration_seconds": round(seconds, 3),
        "error_type": error,
        "http_status": status,
        "response_sha256_of_reserialized_json": None,
        "note": "response digest covers sorted, re-serialized parsed JSON, not raw wire bytes",
    }
    if parsed is not None:
        body = json.dumps(parsed, sort_keys=True, indent=2).encode("utf-8")
        (directory / "endpoint_response_parsed.json").write_bytes(body)
        meta["response_sha256_of_reserialized_json"] = _sha(body)
    (directory / "capture_meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _capturing_post(url, encoded, *, token, timeout_seconds):
    started = time.monotonic()
    parsed, error, status = None, None, None
    try:
        parsed = _original_post(url, encoded, token=token, timeout_seconds=timeout_seconds)
        return parsed
    except Exception as exc:
        error = type(exc).__name__
        status = getattr(exc, "code", None)
        raise
    finally:
        target = os.environ.get("TRACEWELL_CAPTURE_DIR")
        if target:
            _save(Path(target), encoded, parsed, error, status, time.monotonic() - started)


adapter._post = _capturing_post

if __name__ == "__main__":
    raise SystemExit(adapter.main())
