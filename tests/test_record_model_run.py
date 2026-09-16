from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "record_model_run.py"


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def run_recorder(tmp_path: Path, *, missing: str | None = None) -> subprocess.CompletedProcess[str]:
    files = {}
    for name, content in {
        "template": "{{ system }}\n{{ user }}\n",
        "rendered": "System\nJudge this evidence\n",
        "request": '{"messages":[]}',
        "response": '{"choices":[]}',
    }.items():
        path = tmp_path / f"{name}.txt"
        path.write_text(content, encoding="utf-8")
        files[name] = path

    if missing is not None:
        files[missing] = tmp_path / f"missing-{missing}.txt"

    output = tmp_path / "manifest.json"
    command = [
        sys.executable,
        str(SCRIPT),
        "--run-id",
        "tier0-qwen-001",
        "--model-id",
        "Qwen/Qwen2.5-0.5B-Instruct",
        "--hf-revision",
        "0123456789abcdef",
        "--artifact-format",
        "safetensors",
        "--artifact-reference",
        "Qwen/Qwen2.5-0.5B-Instruct@0123456789abcdef",
        "--serving-engine",
        "vllm",
        "--serving-engine-version",
        "test-version",
        "--endpoint",
        "http://127.0.0.1:8000/v1/chat/completions",
        "--decoding-determinism-class",
        "unknown",
        "--generation-parameters",
        '{"temperature":0.0,"max_tokens":256}',
        "--judge-prompt-version",
        "local-openai-compatible-v1",
        "--rubric-version",
        "semantic-rubric-v1",
        "--chat-template",
        str(files["template"]),
        "--rendered-prompt",
        str(files["rendered"]),
        "--request",
        str(files["request"]),
        "--response",
        str(files["response"]),
        "--output",
        str(output),
    ]
    proc = subprocess.run(command, capture_output=True, text=True, check=False, cwd=ROOT)
    proc.output_path = output  # type: ignore[attr-defined]
    proc.files = files  # type: ignore[attr-defined]
    return proc


def test_recorder_hashes_exact_prompt_and_io_files(tmp_path: Path):
    proc = run_recorder(tmp_path)
    assert proc.returncode == 0, proc.stderr

    output = proc.output_path  # type: ignore[attr-defined]
    files = proc.files  # type: ignore[attr-defined]
    manifest = json.loads(output.read_text(encoding="utf-8"))

    assert manifest["model_id"] == "Qwen/Qwen2.5-0.5B-Instruct"
    assert manifest["decoding_determinism_class"] == "unknown"
    assert manifest["chat_template_digest"] == digest(files["template"])
    assert manifest["rendered_prompt_digest"] == digest(files["rendered"])
    assert manifest["request_digest"] == digest(files["request"])
    assert manifest["response_digest"] == digest(files["response"])
    assert manifest["weights_digest"] is None
    assert len(manifest["code_sha"]) == 40


def test_recorder_fails_closed_when_required_provenance_file_is_missing(tmp_path: Path):
    proc = run_recorder(tmp_path, missing="rendered")
    assert proc.returncode != 0
    assert "record_model_run error" in proc.stderr
    assert not proc.output_path.exists()  # type: ignore[attr-defined]
