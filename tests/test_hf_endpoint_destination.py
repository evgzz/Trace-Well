"""Credential-destination checks for dedicated Hugging Face judge adapter.

No network, billing, endpoint credentials or live model required.
"""

from __future__ import annotations

from importlib import util
import io
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "hf_endpoint_judge.py"
GOOD = "abc123.endpoints.huggingface.cloud"


def adapter():
    spec = util.spec_from_file_location("hf_endpoint_judge", ADAPTER)
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("base", [
    f"https://{GOOD}",
    f"https://{GOOD}/",
    f"https://{GOOD}/v1",
    f"https://{GOOD}/v1/",
    f"https://{GOOD.upper()}/v1/",
])
def test_matching_exact_host_is_accepted(base):
    url = adapter()._chat_url(base, allow_http=False, expected_host=GOOD)
    assert url.lower() == f"https://{GOOD}/v1/chat/completions"


@pytest.mark.parametrize("base", [
    "https://evil.example.com",
    f"https://{GOOD}@evil.example.com",
    f"https://evil.example.com@{GOOD}",
    f"https://{GOOD}.evil.example.com",
    f"https://x{GOOD}",
    f"https://{GOOD}:8443",
    f"https://{GOOD}:invalid",
    f"https://{GOOD}/arbitrary",
    f"https://{GOOD}/v1/chat/completions",
    f"https://{GOOD}/v1/?next=other",
    f"https://{GOOD}/v1/#fragment",
    f"https://{GOOD}\n.evil.example",
    f"https://{GOOD}\t.evil.example",
    f"https://{GOOD}/v1\r\n",
    "https://",
])
def test_wrong_or_tricky_urls_are_rejected(base):
    with pytest.raises(ValueError):
        adapter()._chat_url(base, allow_http=False, expected_host=GOOD)


@pytest.mark.parametrize("host", [
    None,
    "",
    " ",
    f"https://{GOOD}",
    f"{GOOD}:443",
    f"*.{GOOD}",
    f"{GOOD}.evil.example",
    "abc..example.com",
])
def test_missing_or_malformed_expected_host_fails_closed(host):
    with pytest.raises(ValueError):
        adapter()._chat_url(f"https://{GOOD}", allow_http=False, expected_host=host)


def test_http_fake_server_path_remains_loopback_only():
    module = adapter()
    assert module._chat_url("http://127.0.0.1:9", allow_http=True) == "http://127.0.0.1:9/v1/chat/completions"
    assert module._chat_url("http://localhost:9090/v1/", allow_http=True) == "http://localhost:9090/v1/chat/completions"
    for bad in ("http://evil.example.com", "http://192.0.2.1", f"http://{GOOD}"):
        with pytest.raises(ValueError):
            module._chat_url(bad, allow_http=True)


def test_https_needs_host_even_with_test_http_flag():
    with pytest.raises(ValueError, match="expected-host"):
        adapter()._chat_url(f"https://{GOOD}", allow_http=True)


def test_wrong_host_aborts_before_post_even_with_token(monkeypatch, capsys):
    """An authenticated bad initial URL cannot reach the network boundary."""
    module = adapter()
    called = []

    def forbidden_network(*args, **kwargs):
        called.append((args, kwargs))
        raise AssertionError("HTTP request must never be issued")

    monkeypatch.setattr(module, "_post", forbidden_network)
    monkeypatch.setenv("HF_TOKEN", "fake-test-secret")
    monkeypatch.setattr(sys, "argv", [
        str(ADAPTER),
        "--base-url", "https://other.example.com",
        "--expected-host", GOOD,
        "--api-model", "endpoint-model",
        "--model", "Qwen/Qwen2.5-0.5B-Instruct",
        "--model-revision", "test-sha",
        "--inference-engine", "vllm",
        "--decoding-determinism-class", "unknown",
        "--rubric-version", "rubric-v1",
    ])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "request_id": "r1",
        "case_id": "c1",
        "trace_id": "t1",
        "construct": "response_supported_by_observable_evidence",
        "rubric": "Assess evidence.",
        "observable_evidence": [{"event_id": "e1", "output": "synthetic"}],
    })))
    assert module.main() == 2
    assert not called
    assert "endpoint hostname does not match" in capsys.readouterr().err
