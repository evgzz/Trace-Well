from __future__ import annotations

import hashlib
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
    last_body: bytes = b""

    def do_POST(self):  # noqa: N802
        assert self.path == "/v1/chat/completions"
        assert self.headers["Authorization"] == "Bearer test-token"
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        type(self).last_body = raw
        payload = json.loads(raw.decode("utf-8"))
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


def run_adapter(
    base_url: str,
    *,
    chat_template: Path | None = None,
    rendered_prompt: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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
        "--allow-http-endpoint",
    ]
    if chat_template is not None:
        command += ["--chat-template-file", str(chat_template)]
    if rendered_prompt is not None:
        command += ["--rendered-prompt-file", str(rendered_prompt)]
    env = {"HF_TOKEN": "test-token"}
    return subprocess.run(
        command,
        input=json.dumps(request_payload().model_dump(mode="json")) + "\n",
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def test_hf_endpoint_adapter_returns_strict_response(tmp_path: Path):
    template = tmp_path / "chat_template.jinja"
    template.write_bytes(b"template-bytes")
    rendered = tmp_path / "rendered_prompt.txt"
    rendered.write_bytes(b"rendered-bytes")
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = run_adapter(
            f"http://127.0.0.1:{port}",
            chat_template=template,
            rendered_prompt=rendered,
        )
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
    assert response.provenance.chat_template_digest == sha256(b"template-bytes")
    assert response.provenance.rendered_prompt_digest == sha256(b"rendered-bytes")
    assert Handler.last_body
    assert response.provenance.request_payload_digest == sha256(Handler.last_body)


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


def test_hf_endpoint_adapter_refuses_redirects_and_never_forwards_token():
    class Target(BaseHTTPRequestHandler):
        hits = 0
        authorization_seen: list[str | None] = []

        def _record(self):
            type(self).hits += 1
            type(self).authorization_seen.append(self.headers.get("Authorization"))
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_GET = do_POST = _record  # urllib downgrades a followed 302 POST to GET

        def log_message(self, format, *args):  # noqa: A003
            return

    target_port = free_port()
    target = ThreadingHTTPServer(("127.0.0.1", target_port), Target)
    target_thread = threading.Thread(target=target.serve_forever, daemon=True)
    target_thread.start()

    class Redirector(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            self.send_response(302)
            self.send_header(
                "Location", f"http://127.0.0.1:{target_port}/v1/chat/completions"
            )
            self.send_header("Content-Length", "0")
            self.end_headers()

        def log_message(self, format, *args):  # noqa: A003
            return

    redirector_port = free_port()
    redirector = ThreadingHTTPServer(("127.0.0.1", redirector_port), Redirector)
    redirector_thread = threading.Thread(target=redirector.serve_forever, daemon=True)
    redirector_thread.start()
    try:
        proc = run_adapter(f"http://127.0.0.1:{redirector_port}")
    finally:
        for server, thread in ((redirector, redirector_thread), (target, target_thread)):
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    # The bearer token never reaches the redirect target.
    assert Target.authorization_seen == []
    assert Target.hits == 0
    assert proc.returncode != 0
    assert "refusing redirect" in proc.stderr
