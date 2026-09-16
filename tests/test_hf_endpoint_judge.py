from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import subprocess
import sys
import threading

from tracewell.semantic_judge import JudgeRequest, JudgeResponse

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = ROOT / "scripts" / "hf_endpoint_judge.py"


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802
        assert self.path == "/v1/chat/completions"
        assert self.headers["Authorization"] == "Bearer test-token"
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        assert payload["model"] == "endpoint-model"
        assert payload["temperature"] == 0.0
        content = {
            "candidate_label": "PASS",
            "observed_value": {"endpoint": True},
            "rationale": "fake dedicated endpoint result",
            "evidence_refs": ["e1"],
        }
        body = json.dumps(
            {"choices": [{"message": {"content": json.dumps(content)}}]}
        ).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


def free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def request_payload() -> JudgeRequest:
    return JudgeRequest(
        request_id="hf-endpoint-1",
        case_id="case-1",
        trace_id="trace-1",
        construct="response_supported_by_observable_evidence",
        rubric="Assess support from observable evidence.",
        observable_evidence=[{"event_id": "e1", "output": "example"}],
    )


def run_adapter(base_url: str) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(ADAPTER),
        "--base-url",
        base_url,
        "--api-model",
        "endpoint-model",
        "--model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--model-revision",
        "rev-123",
        "--inference-engine",
        "vllm",
        "--inference-engine-version",
        "test",
        "--decoding-determinism-class",
        "unknown",
        "--rubric-version",
        "rubric-v1",
        "--chat-template-digest",
        "sha256:" + "a" * 64,
        "--rendered-prompt-digest",
        "sha256:" + "b" * 64,
        "--allow-http-endpoint",
    ]
    env = {"HF_TOKEN": "test-token"}
    return subprocess.run(
        command,
        input=json.dumps(request_payload().model_dump(mode="json")) + "\n",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_hf_endpoint_adapter_returns_strict_response():
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = run_adapter(f"http://127.0.0.1:{port}")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert proc.returncode == 0, proc.stderr
    response = JudgeResponse.model_validate_json(proc.stdout)
    assert response.request_id == "hf-endpoint-1"
    assert response.provenance.execution_mode == "hf_dedicated_endpoint"
    assert response.provenance.model == "Qwen/Qwen2.5-0.5B-Instruct"
    assert response.provenance.model_revision == "rev-123"
    assert response.provenance.inference_engine == "vllm"
    assert response.provenance.chat_template_digest == "sha256:" + "a" * 64
    assert response.provenance.rendered_prompt_digest == "sha256:" + "b" * 64


def test_hf_endpoint_adapter_requires_https_by_default():
    command = [
        sys.executable,
        str(ADAPTER),
        "--base-url",
        "http://example.com",
        "--api-model",
        "endpoint-model",
        "--model",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--model-revision",
        "rev-123",
        "--inference-engine",
        "vllm",
        "--decoding-determinism-class",
        "unknown",
        "--rubric-version",
        "rubric-v1",
    ]
    proc = subprocess.run(
        command,
        input=json.dumps(request_payload().model_dump(mode="json")) + "\n",
        capture_output=True,
        text=True,
        check=False,
        env={"HF_TOKEN": "test-token"},
    )
    assert proc.returncode != 0
    assert "must use https" in proc.stderr
