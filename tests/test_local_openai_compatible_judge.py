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
ADAPTER = ROOT / "scripts" / "local_openai_compatible_judge.py"


class Handler(BaseHTTPRequestHandler):
    response_label = "PASS"

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        payload = json.loads(raw.decode("utf-8"))
        assert payload["model"] == "local-test-model"
        assert payload["temperature"] == 0.0
        assert payload["max_tokens"] == 64
        content = {
            "candidate_label": self.response_label,
            "observed_value": {"checked": True},
            "rationale": "fake local model result",
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


def run_adapter(endpoint: str) -> subprocess.CompletedProcess[str]:
    request = JudgeRequest(
        request_id="req-local-1",
        case_id="case-1",
        trace_id="trace-1",
        construct="semantic_alignment",
        rubric="Assess the observable response.",
        observable_evidence=[
            {
                "event_id": "e1",
                "event_type": "agent_response",
                "actor": "agent",
                "input": None,
                "output": {"action": "continue"},
                "tool": None,
                "tool_arguments": None,
                "tool_result": None,
                "authorization_state": None,
                "evidence_refs": ["e1"],
            }
        ],
    )
    command = [
        sys.executable,
        str(ADAPTER),
        "--endpoint",
        endpoint,
        "--model",
        "local-test-model",
        "--model-revision",
        "test-rev",
        "--inference-engine",
        "fake-openai-compatible",
        "--inference-engine-version",
        "1.0",
        "--decoding-determinism-class",
        "deterministic",
        "--temperature",
        "0",
        "--max-tokens",
        "64",
        "--rubric-version",
        "rubric-v1",
    ]
    return subprocess.run(
        command,
        input=json.dumps(request.model_dump(mode="json")) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )


def test_local_adapter_returns_strict_judge_response():
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = run_adapter(f"http://127.0.0.1:{port}/v1/chat/completions")
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert proc.returncode == 0, proc.stderr
    response = JudgeResponse.model_validate_json(proc.stdout)
    assert response.request_id == "req-local-1"
    assert response.candidate_label.value == "PASS"
    assert response.provenance.judge_id == "tracewell.local-openai-compatible"
    assert response.provenance.model == "local-test-model"
    assert response.provenance.model_revision == "test-rev"
    assert response.provenance.decoding_determinism_class.value == "deterministic"
    assert response.provenance.generation_parameters == {
        "temperature": 0.0,
        "max_tokens": 64,
    }


def test_local_adapter_rejects_non_loopback_endpoint():
    proc = run_adapter("https://example.com/v1/chat/completions")
    assert proc.returncode != 0
    assert "loopback-only" in proc.stderr or "localhost or a loopback IP" in proc.stderr
