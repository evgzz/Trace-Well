#!/usr/bin/env python3
"""Tier-0 hosted-endpoint admission and cleanup (control plane only).

Admission compares authenticated endpoint metadata with independently approved
expectations before any bearer token is sent to the inference host:

  python scripts/tier0_admission.py admit --endpoint-name NAME \
      --configured-url URL --expected-revision SHA

The expected repository is the runner's MODEL_ID (scripts/tier0_hf_run.py), so
admission and recorded provenance cannot name different models.

On success it prints one JSON object (expected_host, origin, endpoint identity)
and exits 0. On any failure it prints nothing to stdout and exits 2.

  python scripts/tier0_admission.py pause --endpoint-name NAME [--namespace NS]

pauses an endpoint that admission already accepted, then polls until its state
reads exactly ``paused``; it exits 2 if that is not confirmed in time. The pause
is requested once. Endpoints are never resumed.

huggingface_hub is optional and imported only inside the live lookup, so the
admission rules can be tested with the base development dependencies.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib import parse

ROOT = Path(__file__).resolve().parents[1]

ADMITTED_STATES = frozenset({"running", "scaledToZero"})
DEFAULT_PAUSE_CONFIRM_SECONDS = 300.0
DEFAULT_PAUSE_POLL_SECONDS = 5.0
_IMMUTABLE_REVISION = re.compile(r"[0-9a-f]{40}")

_spec = importlib.util.spec_from_file_location("hf_endpoint_judge", ROOT / "scripts" / "hf_endpoint_judge.py")
assert _spec is not None and _spec.loader is not None
_adapter = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_adapter)


def expected_repository() -> str:
    """The runner's MODEL_ID: the single source for the admitted repository."""
    spec = importlib.util.spec_from_file_location("tier0_hf_run", ROOT / "scripts" / "tier0_hf_run.py")
    assert spec is not None and spec.loader is not None
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    return runner.MODEL_ID


class AdmissionError(ValueError):
    """Endpoint metadata or configuration does not admit token-bearing calls."""


def _status_text(status: Any) -> str | None:
    value = getattr(status, "value", status)
    return value if isinstance(value, str) else None


def _require_positive_seconds(value: float, name: str) -> float:
    if not (isinstance(value, (int, float)) and math.isfinite(value) and value > 0):
        raise ValueError(f"{name} must be a finite number of seconds greater than 0")
    return value


def _seconds_arg(text: str) -> float:
    try:
        return _require_positive_seconds(float(text), "value")
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _live_lookup(name: str, namespace: str | None):
    from huggingface_hub import get_inference_endpoint

    return get_inference_endpoint(name, namespace=namespace)


def fetch_metadata(name: str, namespace: str | None = None) -> dict[str, Any]:
    """Authenticated control-plane lookup through the lazy huggingface_hub import."""
    endpoint = _live_lookup(name, namespace)
    return {
        "name": endpoint.name,
        "namespace": endpoint.namespace,
        "status": _status_text(endpoint.status),
        "url": endpoint.url,
        "repository": endpoint.repository,
        "revision": endpoint.revision,
    }


def admit(
    metadata: dict[str, Any],
    *,
    configured_url: str,
    expected_repository: str,
    expected_revision: str,
) -> dict[str, str]:
    """Return the admitted destination, or raise AdmissionError.

    Expected values must be chosen before the lookup; never copy them from
    ``metadata``, or the comparison proves nothing.
    """
    if not _IMMUTABLE_REVISION.fullmatch(expected_revision or ""):
        raise AdmissionError("expected revision must be a 40-character lowercase commit SHA")

    for key in ("name", "status", "url", "repository", "revision"):
        if not isinstance(metadata.get(key), str) or not metadata[key]:
            raise AdmissionError(f"endpoint metadata is missing {key}")

    if metadata["status"] not in ADMITTED_STATES:
        raise AdmissionError(f"endpoint state {metadata['status']!r} is not admitted")
    if metadata["repository"] != expected_repository:
        raise AdmissionError("endpoint repository does not match the expected repository")
    if metadata["revision"] != expected_revision:
        raise AdmissionError("endpoint revision does not match the expected revision")

    control_plane = parse.urlsplit(metadata["url"])
    if control_plane.scheme != "https" or not control_plane.hostname:
        raise AdmissionError("control-plane endpoint URL is not HTTPS")
    expected_host = control_plane.hostname.lower()

    try:
        # Same exact-host rules as the adapter, applied to both URLs.
        _adapter._chat_url(metadata["url"], allow_http=False, expected_host=expected_host)
        _adapter._chat_url(configured_url, allow_http=False, expected_host=expected_host)
    except ValueError as exc:
        raise AdmissionError(str(exc)) from exc

    return {
        "endpoint_name": metadata["name"],
        "namespace": metadata.get("namespace") or "",
        "status": metadata["status"],
        "repository": metadata["repository"],
        "revision": metadata["revision"],
        "expected_host": expected_host,
        "origin": f"https://{expected_host}",
    }


def pause(
    name: str,
    namespace: str | None = None,
    *,
    confirm_timeout: float = DEFAULT_PAUSE_CONFIRM_SECONDS,
    poll_interval: float = DEFAULT_PAUSE_POLL_SECONDS,
    lookup=_live_lookup,
    sleep=time.sleep,
    clock=time.monotonic,
) -> str:
    """Request one pause, then poll state until it reads exactly ``paused``.

    The pause mutation is issued once; only the state is re-read. Raises
    AdmissionError if ``paused`` is not confirmed within ``confirm_timeout``.
    The deadline bounds the polling loop only; a control-plane call that
    blocks is bounded by the caller (tier0_codespace.sh wraps this command
    in ``timeout``).
    """
    _require_positive_seconds(confirm_timeout, "confirm_timeout")
    _require_positive_seconds(poll_interval, "poll_interval")
    endpoint = lookup(name, namespace)
    endpoint.pause()
    deadline = clock() + confirm_timeout
    while True:
        endpoint.fetch()
        state = _status_text(endpoint.status)
        if state == "paused":
            return state
        if clock() >= deadline:
            raise AdmissionError(f"pause not confirmed within {confirm_timeout:g}s; last state {state!r}")
        # Never sleep past the deadline, so the wait stays bounded by confirm_timeout.
        sleep(min(poll_interval, max(0.0, deadline - clock())))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    admit_parser = sub.add_parser("admit")
    admit_parser.add_argument("--endpoint-name", required=True)
    admit_parser.add_argument("--namespace")
    admit_parser.add_argument("--configured-url", required=True)
    admit_parser.add_argument("--expected-revision", required=True)
    pause_parser = sub.add_parser("pause")
    pause_parser.add_argument("--endpoint-name", required=True)
    pause_parser.add_argument("--namespace")
    pause_parser.add_argument("--confirm-timeout", type=_seconds_arg, default=DEFAULT_PAUSE_CONFIRM_SECONDS)
    pause_parser.add_argument("--poll-interval", type=_seconds_arg, default=DEFAULT_PAUSE_POLL_SECONDS)
    args = parser.parse_args(argv)

    try:
        if args.command == "admit":
            result = admit(
                fetch_metadata(args.endpoint_name, args.namespace or None),
                configured_url=args.configured_url,
                expected_repository=expected_repository(),
                expected_revision=args.expected_revision,
            )
            sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        else:
            state = pause(
                args.endpoint_name,
                args.namespace or None,
                confirm_timeout=args.confirm_timeout,
                poll_interval=args.poll_interval,
            )
            print("endpoint status after pause:", state)
    except Exception as exc:
        print(f"tier0 {args.command} refused: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
