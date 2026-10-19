"""Tier-0 hosted harness: admission, protected request paths, payload contract.

No network, billing, endpoint credentials, live model or huggingface_hub required.
A fake huggingface_hub package and a recording fake curl stand in for the
control plane and the inference host.
"""

from __future__ import annotations

from importlib import util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tracewell.semantic_judge import JudgeRequest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
GOLDEN = Path(__file__).parent / "fixtures" / "hf_endpoint_default_payload.json"
MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
REVISION = "7ae557604adf67be50417f59c2c2f167def9a775"
HOST = "abc123.endpoints.huggingface.cloud"


def load(name: str):
    spec = util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def metadata(**overrides):
    value = {
        "name": "tier0-qwen",
        "namespace": "example-org",
        "status": "running",
        "url": f"https://{HOST}",
        "repository": MODEL,
        "revision": REVISION,
    }
    value.update(overrides)
    return value


ADMISSION = load("tier0_admission")


def admit(meta, configured_url=f"https://{HOST}", revision=REVISION, repository=MODEL):
    return ADMISSION.admit(
        meta, configured_url=configured_url, expected_repository=repository, expected_revision=revision
    )


# --- admission rules ---------------------------------------------------------


@pytest.mark.parametrize("state", ["running", "scaledToZero"])
def test_admitted_states_return_control_plane_host(state):
    result = admit(metadata(status=state))
    assert result["expected_host"] == HOST
    assert result["origin"] == f"https://{HOST}"
    assert result["endpoint_name"] == "tier0-qwen"


@pytest.mark.parametrize("state", [
    "paused", "pending", "initializing", "failed", "updateFailed", "Running",
    "notrunning", "running ", "scaledToZeroPending", "", None, 1,
])
def test_disallowed_or_unknown_states_are_rejected(state):
    module = load("tier0_admission")
    with pytest.raises(module.AdmissionError):
        module.admit(metadata(status=state), configured_url=f"https://{HOST}",
                     expected_repository=MODEL, expected_revision=REVISION)


@pytest.mark.parametrize("key", ["name", "status", "url", "repository", "revision"])
@pytest.mark.parametrize("missing", [None, ""])
def test_missing_metadata_is_rejected(key, missing):
    module = load("tier0_admission")
    with pytest.raises(module.AdmissionError, match="missing"):
        module.admit(metadata(**{key: missing}), configured_url=f"https://{HOST}",
                     expected_repository=MODEL, expected_revision=REVISION)


@pytest.mark.parametrize("meta, kwargs, message", [
    (metadata(repository="Qwen/Qwen2.5-7B-Instruct"), {}, "repository"),
    (metadata(revision="0" * 40), {}, "revision"),
    (metadata(), {"revision": "main"}, "40-character"),
    (metadata(), {"revision": REVISION.upper()}, "40-character"),
    (metadata(), {"configured_url": "https://evil.example.com"}, "does not match"),
    (metadata(), {"configured_url": f"https://{HOST}.evil.example"}, "does not match"),
    (metadata(), {"configured_url": f"https://{HOST}/v1/chat/completions"}, "origin"),
    (metadata(url=f"http://{HOST}"), {}, "HTTPS"),
    (metadata(url=f"https://{HOST}/other"), {}, "origin"),
])
def test_identity_and_destination_mismatches_are_rejected(meta, kwargs, message):
    with pytest.raises(ADMISSION.AdmissionError, match=message):
        admit(meta, **kwargs)


def test_admission_module_imports_without_huggingface_hub(monkeypatch):
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)
    module = load("tier0_admission")
    with pytest.raises(ImportError):
        module.fetch_metadata("tier0-qwen")


# --- runner forwarding and payload contract ---------------------------------


def test_runner_forwards_expected_host_to_adapter(monkeypatch):
    monkeypatch.setenv("HF_ENDPOINT_URL", f"https://{HOST}")
    monkeypatch.setenv("HF_EXPECTED_HOST", HOST)
    monkeypatch.setenv("HF_API_MODEL", MODEL)
    monkeypatch.setenv("HF_REVISION", REVISION)
    monkeypatch.setenv("HF_ENGINE", "vllm")
    command = load("tier0_hf_run").judge_command()
    assert command[command.index("--expected-host") + 1] == HOST
    assert command[command.index("--base-url") + 1] == f"https://{HOST}"


def test_runner_refuses_to_build_command_without_expected_host(monkeypatch):
    monkeypatch.setenv("HF_ENDPOINT_URL", f"https://{HOST}")
    monkeypatch.delenv("HF_EXPECTED_HOST", raising=False)
    with pytest.raises(SystemExit, match="HF_EXPECTED_HOST"):
        load("tier0_hf_run").judge_command()


def payload_args(**overrides):
    from types import SimpleNamespace

    values = dict(api_model=MODEL, temperature=0.0, max_tokens=256, seed=None, response_schema=False)
    values.update(overrides)
    return SimpleNamespace(**values)


def fixed_request() -> JudgeRequest:
    return JudgeRequest(
        request_id="golden-r1",
        case_id="golden-case",
        trace_id="golden-trace",
        construct="response_supported_by_observable_evidence",
        rubric="Assess whether the response is supported by the observable evidence.",
        observable_evidence=[{"event_id": "e1", "output": "synthetic observable output"}],
    )


def test_default_payload_bytes_match_committed_golden_fixture():
    """Update the fixture only for an intended, explained request-contract change."""
    adapter = load("hf_endpoint_judge")
    encoded = adapter._encode(adapter._model_payload(fixed_request(), payload_args()))
    assert encoded == GOLDEN.read_bytes()


def test_response_schema_changes_only_response_format():
    adapter = load("hf_endpoint_judge")
    base = json.loads(adapter._encode(adapter._model_payload(fixed_request(), payload_args())))
    schema = json.loads(adapter._encode(adapter._model_payload(fixed_request(), payload_args(response_schema=True))))
    assert schema.pop("response_format")["json_schema"]["schema"] == adapter.JUDGE_RESPONSE_SCHEMA
    assert schema == base


def test_adapter_accepts_schema_and_expected_host_together():
    adapter = load("hf_endpoint_judge")
    args = adapter.parser().parse_args([
        "--base-url", f"https://{HOST}", "--expected-host", HOST, "--response-schema",
        "--api-model", MODEL, "--model", MODEL, "--model-revision", REVISION,
        "--inference-engine", "vllm", "--decoding-determinism-class", "unknown",
        "--rubric-version", "semantic-rubric-v1",
    ])
    assert args.response_schema is True
    assert adapter._chat_url(args.base_url, allow_http=False, expected_host=args.expected_host) == (
        f"https://{HOST}/v1/chat/completions"
    )


# --- shell orchestration: all protected paths -------------------------------

FAKE_HUB = """
import json, os

class _Endpoint:
    def __init__(self, name, namespace):
        meta = json.loads(os.environ["FAKE_HF_METADATA"])
        self.name = meta.get("name")
        self.namespace = meta.get("namespace")
        self.status = meta.get("status")
        self.url = meta.get("url")
        self.repository = meta.get("repository")
        self.revision = meta.get("revision")

    def pause(self):
        if os.environ.get("FAKE_HF_PAUSE_HANG"):
            import time
            time.sleep(float(os.environ["FAKE_HF_PAUSE_HANG"]))
        if os.environ.get("FAKE_HF_PAUSE_FAIL") == "1":
            raise RuntimeError("simulated pause failure")
        with open(os.environ["FAKE_HF_PAUSE_LOG"], "a") as handle:
            handle.write(json.dumps({"name": self.name, "namespace": self.namespace}) + "\\n")
        self._after_pause = os.environ.get("FAKE_HF_PAUSE_STATES", "paused").split(",")

    def fetch(self):
        states = getattr(self, "_after_pause", None)
        if states:
            self.status = states.pop(0) if len(states) > 1 else states[0]
        return self

def get_inference_endpoint(name, namespace=None, token=None):
    return _Endpoint(name, namespace)
"""

# Loaded by every Python process the script starts. It blocks Python socket
# connect attempts (not a full sandbox), and records then stops any judge
# process (G3/G4) before it can send anything, wherever the script starts it.
SITECUSTOMIZE = """
import json, os, socket, sys

def _log(name, record):
    with open(os.environ[name], "a") as handle:
        handle.write(json.dumps(record) + "\\n")

def _refuse(self, address, *args, **kwargs):
    _log("FAKE_NET_LOG", {"argv0": sys.argv[0], "address": repr(address)})
    raise OSError("network disabled in tier0 harness tests")

socket.socket.connect = _refuse
socket.socket.connect_ex = _refuse

if os.path.basename(sys.argv[0]) in ("tier0_capture_judge.py", "hf_endpoint_judge.py"):
    _log("FAKE_JUDGE_LOG", sys.argv)
    sys.stderr.write("judge intercepted by test harness\\n")
    raise SystemExit(3)
"""

FAKE_CURL = """#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
with open(os.environ["FAKE_CURL_LOG"], "a") as handle:
    handle.write(json.dumps(argv) + "\\n")
out = argv[argv.index("-o") + 1] if "-o" in argv else None
url = next(a for a in argv if a.startswith("http"))
authed = any(a.startswith("Authorization:") for a in argv)
if not authed:
    status, body = "401", "{}"
elif url.endswith("/v1/models"):
    status = os.environ.get("FAKE_CURL_WAKE_STATUS", "200")
    body = json.dumps({"data": [{"id": os.environ["HF_API_MODEL"]}]})
else:
    status = "200"
    body = json.dumps({"choices": [{"finish_reason": "stop", "message": {"content": "{}"}}]})
if out and out != "/dev/null":
    open(out, "w").write(body)
sys.stdout.write(status)
"""


@pytest.fixture
def harness(tmp_path):
    if shutil.which("bash") is None:
        pytest.skip("bash unavailable")
    fake_lib = tmp_path / "fake_lib"
    (fake_lib / "huggingface_hub").mkdir(parents=True)
    (fake_lib / "huggingface_hub" / "__init__.py").write_text(FAKE_HUB, encoding="utf-8")
    (fake_lib / "sitecustomize.py").write_text(SITECUSTOMIZE, encoding="utf-8")
    fake_bin = tmp_path / "fake_bin"
    fake_bin.mkdir()
    curl = fake_bin / "curl"
    curl.write_text(FAKE_CURL, encoding="utf-8")
    curl.chmod(0o755)
    out = tmp_path / "out"
    logs = {name: tmp_path / f"{name}.log" for name in ("curl", "judge", "net", "pause")}

    def read(name):
        path = logs[name]
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []

    def run(meta=None, **env_overrides):
        env = {
            key: value for key, value in os.environ.items()
            if not key.startswith(("HF_", "TIER0_", "FAKE_"))
        }
        env.update(
            PATH=f"{fake_bin}{os.pathsep}{Path(sys.executable).parent}{os.pathsep}{os.environ['PATH']}",
            PYTHONPATH=f"{fake_lib}{os.pathsep}{ROOT}",
            HF_TOKEN="fake-test-secret",
            HF_ENDPOINT_URL=f"https://{HOST}/v1/",
            HF_ENDPOINT_NAME="tier0-qwen",
            HF_REVISION=REVISION,
            TIER0_SKIP_SETUP="1",
            TIER0_REPEATS="1",
            TIER0_OUT_DIR=str(out),
            TIER0_PAUSE_CONFIRM_SECONDS="0.5",
            TIER0_PAUSE_POLL_SECONDS="0.05",
            TIER0_PAUSE_COMMAND_SECONDS="20",
            FAKE_HF_METADATA=json.dumps(metadata() if meta is None else meta),
            FAKE_HF_PAUSE_LOG=str(logs["pause"]),
            FAKE_CURL_LOG=str(logs["curl"]),
            FAKE_JUDGE_LOG=str(logs["judge"]),
            FAKE_NET_LOG=str(logs["net"]),
        )
        env.update(env_overrides)
        proc = subprocess.run(
            ["bash", str(SCRIPTS / "tier0_codespace.sh")],
            cwd=ROOT, env=env, capture_output=True, text=True, timeout=120,
        )
        return SimpleNamespace(
            proc=proc, out=out, curl=read("curl"), judge=read("judge"),
            net=read("net"), pauses=read("pause"),
        )

    return run


def token_calls(result):
    return [c for c in result.curl if any(a.startswith("Authorization:") for a in c)]


def assert_protected_paths_untouched(result):
    assert token_calls(result) == []  # G1 wake-up and G2 direct request: not invoked
    assert result.judge == []  # G3/G4 judge process: not invoked
    assert result.net == []  # no Python socket connect attempt
    # Secondary evidence only; the invocation logs above are the proof.
    assert not (result.out / "raw_request.json").exists()
    assert not (result.out / "run_summary.json").exists()


@pytest.mark.parametrize("meta, env, message", [
    (metadata(status="paused"), {}, "not admitted"),
    (metadata(status="failed"), {}, "not admitted"),
    (metadata(status=None), {}, "missing status"),
    (metadata(url=None), {}, "missing url"),
    (metadata(repository="other/model"), {}, "repository"),
    (metadata(revision="1" * 40), {}, "revision"),
    (metadata(), {"HF_ENDPOINT_URL": "https://evil.example.com"}, "does not match"),
])
def test_shell_admission_failure_blocks_all_protected_paths(harness, meta, env, message):
    result = harness(meta, **env)
    assert result.proc.returncode != 0
    assert message in result.proc.stderr
    assert "no token was sent" in result.proc.stderr
    assert result.curl == []
    assert_protected_paths_untouched(result)
    assert result.pauses == []  # an unadmitted endpoint is never paused


def test_shell_requires_explicit_revision(harness):
    result = harness(HF_REVISION="")
    assert result.proc.returncode != 0
    assert "HF_REVISION" in result.proc.stderr
    assert result.curl == [] and result.pauses == []
    assert_protected_paths_untouched(result)


@pytest.mark.parametrize("state", ["running", "scaledToZero"])
def test_shell_admitted_run_reaches_every_path_on_admitted_origin(harness, state):
    result = harness(metadata(status=state))
    assert result.proc.returncode == 0, result.proc.stdout + result.proc.stderr
    assert len(result.curl) == 3  # anonymous probe, G1 wake-up, G2 direct request
    for argv in result.curl:
        assert argv[:2] == ["-q", "--proto"] and argv[2] == "=https"
        assert "--max-redirs" in argv and argv[argv.index("--max-redirs") + 1] == "0"
        assert "-L" not in argv and "--location" not in argv
        assert argv[argv.index("--connect-timeout") + 1] == "30"
        assert argv[argv.index("--max-time") + 1] == "660"
        url = next(a for a in argv if a.startswith("http"))
        assert url.startswith(f"https://{HOST}/v1/")
    assert [any(a.startswith("Authorization:") for a in c) for c in result.curl] == [False, True, True]
    assert all("--fail-with-body" in c for c in result.curl[1:])

    assert len(result.judge) == 1  # G3/G4: one repetition, intercepted before sending
    judge_argv = result.judge[0]
    assert judge_argv[judge_argv.index("--base-url") + 1] == f"https://{HOST}"
    assert judge_argv[judge_argv.index("--expected-host") + 1] == HOST
    assert result.net == []

    assert json.loads((result.out / "admission.json").read_text())["expected_host"] == HOST
    assert result.pauses == [{"name": "tier0-qwen", "namespace": "example-org"}]
    assert not (result.out / "cleanup_failed.txt").exists()


def test_shell_failure_after_admission_still_pauses(harness):
    result = harness(FAKE_CURL_WAKE_STATUS="503")
    assert result.proc.returncode != 0
    assert "Endpoint not ready (HTTP 503)" in result.proc.stdout
    assert len(result.curl) == 2  # stopped before G2
    assert result.judge == []
    assert len(result.pauses) == 1


def test_shell_pause_failure_after_clean_run_exits_nonzero(harness):
    result = harness(FAKE_HF_PAUSE_FAIL="1")
    assert result.proc.returncode == 3
    assert "PAUSE NOT CONFIRMED" in result.proc.stderr
    assert (result.out / "cleanup_failed.txt").is_file()
    assert (result.out / "run_summary.json").is_file()  # transport evidence kept apart


def test_shell_pause_failure_keeps_original_failure_status(harness):
    result = harness(FAKE_HF_PAUSE_FAIL="1", FAKE_CURL_WAKE_STATUS="503")
    assert result.proc.returncode == 1
    assert (result.out / "cleanup_failed.txt").is_file()


def test_shell_pause_can_be_disabled_after_admission(harness):
    result = harness(TIER0_PAUSE_ON_EXIT="0")
    assert result.proc.returncode == 0, result.proc.stdout + result.proc.stderr
    assert result.pauses == []


def test_admission_repository_is_the_runner_model_id():
    assert ADMISSION.expected_repository() == load("tier0_hf_run").MODEL_ID
    shell = (SCRIPTS / "tier0_codespace.sh").read_text(encoding="utf-8")
    assert "MODEL_ID" not in shell and "--expected-repository" not in shell


@pytest.mark.parametrize("states", ["running", "pausing", "failed"])
def test_shell_unconfirmed_pause_after_clean_run_exits_nonzero(harness, states):
    result = harness(FAKE_HF_PAUSE_STATES=states)
    assert result.proc.returncode == 3
    assert "PAUSE NOT CONFIRMED" in result.proc.stderr
    assert "pause not confirmed" in result.proc.stderr
    assert (result.out / "cleanup_failed.txt").is_file()
    assert (result.out / "run_summary.json").is_file()
    assert len(result.pauses) == 1  # the pause mutation is issued once


def test_shell_transitional_state_then_paused_succeeds(harness):
    result = harness(FAKE_HF_PAUSE_STATES="running,pausing,paused")
    assert result.proc.returncode == 0, result.proc.stdout + result.proc.stderr
    assert len(result.pauses) == 1
    assert not (result.out / "cleanup_failed.txt").exists()


def test_shell_unconfirmed_pause_keeps_original_failure_status(harness):
    result = harness(FAKE_HF_PAUSE_STATES="running", FAKE_CURL_WAKE_STATUS="503")
    assert result.proc.returncode == 1
    assert (result.out / "cleanup_failed.txt").is_file()


# --- pause confirmation loop -------------------------------------------------


class FakeEndpoint:
    def __init__(self, states, pause_error=None):
        self.states = list(states)
        self.status = "running"
        self.pause_calls = 0
        self.fetch_calls = 0
        self.pause_error = pause_error

    def pause(self):
        self.pause_calls += 1
        if self.pause_error:
            raise self.pause_error

    def fetch(self):
        self.fetch_calls += 1
        self.status = self.states.pop(0) if len(self.states) > 1 else self.states[0]
        return self


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


def run_pause(endpoint, timeout=30.0, interval=5.0):
    clock = FakeClock()
    state = ADMISSION.pause(
        "tier0-qwen", None, confirm_timeout=timeout, poll_interval=interval,
        lookup=lambda name, namespace: endpoint, sleep=clock.sleep, clock=clock,
    )
    return state, clock


def test_pause_confirmed_immediately():
    endpoint = FakeEndpoint(["paused"])
    state, clock = run_pause(endpoint)
    assert state == "paused"
    assert endpoint.pause_calls == 1 and endpoint.fetch_calls == 1
    assert clock.now == 0.0


def test_pause_confirmed_after_transitional_states_without_reissuing():
    endpoint = FakeEndpoint(["running", "pausing", "paused"])
    state, clock = run_pause(endpoint)
    assert state == "paused"
    assert endpoint.pause_calls == 1 and endpoint.fetch_calls == 3
    assert clock.now == 10.0


@pytest.mark.parametrize("stuck", ["running", "pausing", "scaledToZero", "failed", None])
def test_pause_not_confirmed_fails_after_bounded_wait(stuck):
    endpoint = FakeEndpoint([stuck])
    with pytest.raises(ADMISSION.AdmissionError, match="not confirmed"):
        run_pause(endpoint, timeout=30.0, interval=5.0)
    assert endpoint.pause_calls == 1
    assert endpoint.fetch_calls == 7  # t = 0, 5, ... 30, then give up


def test_pause_request_error_propagates_without_polling():
    endpoint = FakeEndpoint(["paused"], pause_error=RuntimeError("api down"))
    with pytest.raises(RuntimeError, match="api down"):
        run_pause(endpoint)
    assert endpoint.fetch_calls == 0


# --- pause settings are validated and the wait is bounded ---------------------


@pytest.mark.parametrize("flag", ["--confirm-timeout", "--poll-interval"])
@pytest.mark.parametrize("value", ["inf", "-inf", "nan", "0", "0.0", "-1", "abc"])
def test_pause_cli_rejects_invalid_seconds(flag, value, capsys):
    with pytest.raises(SystemExit) as excinfo:
        ADMISSION.main(["pause", "--endpoint-name", "tier0-qwen", flag, value])
    assert excinfo.value.code == 2
    err = capsys.readouterr().err
    if not value.startswith("-") and value != "abc":  # argparse reads "-x" as an option
        assert "greater than 0" in err


@pytest.mark.parametrize("kwargs", [
    {"confirm_timeout": float("inf")}, {"confirm_timeout": float("nan")}, {"confirm_timeout": 0},
    {"poll_interval": float("inf")}, {"poll_interval": float("nan")}, {"poll_interval": 0},
])
def test_pause_rejects_invalid_seconds_before_any_call(kwargs):
    looked_up = []
    with pytest.raises(ValueError, match="greater than 0"):
        ADMISSION.pause("tier0-qwen", lookup=lambda *a: looked_up.append(a), **kwargs)
    assert looked_up == []  # no control-plane call, no pause request


def test_poll_sleep_never_passes_the_deadline():
    endpoint = FakeEndpoint(["running"])
    with pytest.raises(ADMISSION.AdmissionError, match="not confirmed"):
        clock = FakeClock()
        try:
            ADMISSION.pause(
                "tier0-qwen", confirm_timeout=30.0, poll_interval=50.0,
                lookup=lambda *a: endpoint, sleep=clock.sleep, clock=clock,
            )
        finally:
            assert clock.now == 30.0  # slept 30, not 50
    assert endpoint.fetch_calls == 2


@pytest.mark.parametrize("name", [
    "TIER0_PAUSE_CONFIRM_SECONDS", "TIER0_PAUSE_POLL_SECONDS", "TIER0_PAUSE_COMMAND_SECONDS",
    "TIER0_CURL_CONNECT_SECONDS", "TIER0_CURL_MAX_SECONDS",
])
@pytest.mark.parametrize("value", [
    "inf", "nan", "0", "0.0", "-1", "1e3", "abc",
    "1" * 400,  # decimal syntax, but inf in Python and awk
    "100000", "1.2345",
])
def test_shell_rejects_invalid_timing_settings_before_admission(harness, name, value):
    result = harness(**{name: value})
    assert result.proc.returncode == 2
    assert name in result.proc.stderr
    assert result.curl == [] and result.pauses == []
    assert not (result.out / "admission.json").exists()
    assert_protected_paths_untouched(result)


def test_shell_requires_curl_limit_above_scale_up_timeout(harness):
    result = harness(TIER0_CURL_MAX_SECONDS="600")
    assert result.proc.returncode == 2
    assert "scale-up timeout" in result.proc.stderr
    assert result.curl == []


def test_shell_requires_command_bound_above_confirm_wait(harness):
    result = harness(TIER0_PAUSE_CONFIRM_SECONDS="30", TIER0_PAUSE_COMMAND_SECONDS="30")
    assert result.proc.returncode == 2
    assert "must exceed" in result.proc.stderr
    assert result.curl == []


@pytest.mark.skipif(shutil.which("timeout") is None, reason="GNU timeout unavailable")
def test_shell_blocked_pause_call_is_bounded_and_fails(harness):
    result = harness(FAKE_HF_PAUSE_HANG="60", TIER0_PAUSE_COMMAND_SECONDS="1")
    assert result.proc.returncode == 3
    assert "PAUSE NOT CONFIRMED" in result.proc.stderr
    assert (result.out / "cleanup_failed.txt").is_file()
    assert (result.out / "run_summary.json").is_file()
