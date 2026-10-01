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
ADAPTER = ROOT / "scripts" / "local_openai_compatible_judge.py"


class Handler(BaseHTTPRequestHandler):
    response_label = "PASS"
    last_body: bytes = b""

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        type(self).last_body = raw
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


def run_adapter(
    endpoint: str,
    *,
    chat_template: Path | None = None,
    rendered_prompt: Path | None = None,
) -> subprocess.CompletedProcess[str]:
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
    if chat_template is not None:
        command += ["--chat-template-file", str(chat_template)]
    if rendered_prompt is not None:
        command += ["--rendered-prompt-file", str(rendered_prompt)]
    return subprocess.run(
        command,
        input=json.dumps(request.model_dump(mode="json")) + "\n",
        capture_output=True,
        text=True,
        check=False,
    )


def sha256(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def serve(handler) -> tuple[ThreadingHTTPServer, threading.Thread, int]:
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread, port


def stop(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    thread.join(timeout=2)
    server.server_close()


def test_local_adapter_returns_strict_judge_response(tmp_path: Path):
    template = tmp_path / "chat_template.jinja"
    template.write_bytes(b"{{ messages }}")
    rendered = tmp_path / "rendered_prompt.txt"
    rendered.write_bytes(b"<|system|>rendered")
    port = free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        proc = run_adapter(
            f"http://127.0.0.1:{port}/v1/chat/completions",
            chat_template=template,
            rendered_prompt=rendered,
        )
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
    # Digests are computed by the adapter from actual bytes, not asserted.
    assert response.provenance.chat_template_digest == sha256(b"{{ messages }}")
    assert response.provenance.rendered_prompt_digest == sha256(b"<|system|>rendered")
    assert Handler.last_body
    assert response.provenance.request_payload_digest == sha256(Handler.last_body)
    assert response.provenance.generation_parameters == {
        "temperature": 0.0,
        "max_tokens": 64,
    }


def test_local_adapter_rejects_non_loopback_endpoint():
    proc = run_adapter("https://example.com/v1/chat/completions")
    assert proc.returncode != 0
    assert "loopback-only" in proc.stderr or "localhost or a loopback IP" in proc.stderr


def test_local_adapter_digests_are_null_without_source_files():
    server, thread, port = serve(Handler)
    try:
        proc = run_adapter(f"http://127.0.0.1:{port}/v1/chat/completions")
    finally:
        stop(server, thread)

    assert proc.returncode == 0, proc.stderr
    response = JudgeResponse.model_validate_json(proc.stdout)
    assert response.provenance.chat_template_digest is None
    assert response.provenance.rendered_prompt_digest is None
    assert response.provenance.request_payload_digest == sha256(Handler.last_body)


def test_local_adapter_refuses_redirects():
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

    target, target_thread, target_port = serve(Target)

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

    redirector, redirector_thread, redirector_port = serve(Redirector)
    try:
        proc = run_adapter(f"http://127.0.0.1:{redirector_port}/v1/chat/completions")
    finally:
        stop(redirector, redirector_thread)
        stop(target, target_thread)

    assert Target.hits == 0
    assert proc.returncode != 0
    assert "refusing redirect" in proc.stderr
