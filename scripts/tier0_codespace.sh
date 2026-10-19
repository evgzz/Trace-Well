#!/usr/bin/env bash
# Tier-0 hosted-endpoint run for GitHub Codespaces (transport_only evidence).
# Requires: Codespaces secret HF_TOKEN, a running dedicated endpoint, repo root as cwd.
# Always attempts to pause the endpoint on exit unless TIER0_PAUSE_ON_EXIT=0.
set -euo pipefail

: "${HF_TOKEN:?Set HF_TOKEN as a Codespaces secret, then restart the codespace}"
: "${HF_ENDPOINT_URL:?export HF_ENDPOINT_URL=https://<endpoint-host>}"
export HF_ENDPOINT_NAME="${HF_ENDPOINT_NAME:-qwen2-5-0-5b-instruct-vqa}"
export HF_API_MODEL="${HF_API_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
export HF_REVISION="${HF_REVISION:-7ae557604adf67be50417f59c2c2f167def9a775}"
export HF_ENGINE="${HF_ENGINE:-vllm}"
export RUN_ID="${RUN_ID:-tier0-qwen-hf-001}"
TIER0_PAUSE_ON_EXIT="${TIER0_PAUSE_ON_EXIT:-1}"

HF_ENDPOINT_URL="${HF_ENDPOINT_URL%/}"
HF_ENDPOINT_URL="${HF_ENDPOINT_URL%/v1}"
export HF_ENDPOINT_URL

OUT="results/real-model/${RUN_ID}"
mkdir -p "$OUT"

endpoint_state() {
  python - <<'PY'
import os
from huggingface_hub import get_inference_endpoint
ep = get_inference_endpoint(os.environ["HF_ENDPOINT_NAME"])
print(getattr(ep.status, "value", str(ep.status)))
PY
}

cleanup() {
  status=$?
  if [ "$TIER0_PAUSE_ON_EXIT" = "1" ]; then
    echo "== cleanup: pausing endpoint $HF_ENDPOINT_NAME"
    python - <<'PY' || echo "!! PAUSE FAILED: pause it manually in the dashboard NOW"
import os
from huggingface_hub import get_inference_endpoint
ep = get_inference_endpoint(os.environ["HF_ENDPOINT_NAME"])
ep.pause()
ep.fetch()
print("endpoint status after pause:", getattr(ep.status, "value", str(ep.status)))
PY
    echo "$(date -u +%FT%TZ) $(endpoint_state 2>/dev/null || echo unknown)" > "$OUT/endpoint_state_after.txt"
  fi
  echo "== exit status $status. Revoke the run token after confirming 'paused'."
  exit $status
}
case "$HF_ENDPOINT_URL" in
  https://*'<'*|https://*'>'*|https://*' '*|"") echo "HF_ENDPOINT_URL looks like a placeholder"; exit 2 ;;
  https://*) ;;
  *) echo "HF_ENDPOINT_URL must start with https://"; exit 2 ;;
esac

trap cleanup EXIT

echo "== G0: branch, ignore rule, baseline"
branch="$(git branch --show-current)"
if [ "$branch" = "main" ]; then echo "Refusing to run on main"; exit 1; fi
grep -qx "results/real-model/" .gitignore || { echo "Add 'results/real-model/' to .gitignore first"; exit 1; }
python -m pip install -q -e '.[dev]' huggingface_hub
pytest -q
python scripts/check_public_text.py

echo "== G1: endpoint identity and state"
date -u +%FT%TZ > "$OUT/started_utc.txt"
state="$(endpoint_state)"
echo "endpoint state: $state"
echo "$state" > "$OUT/endpoint_state_before.txt"
case "$state" in
  *running*|*scaledToZero*) ;;
  *) echo "Endpoint is '$state'; resume it in the dashboard or: hf endpoints resume $HF_ENDPOINT_NAME"; exit 1 ;;
esac

echo "== auth enforcement (expect 401/403) and wake-up (expect 200)"
anon="$(curl -sS -o /dev/null -w '%{http_code}' "$HF_ENDPOINT_URL/v1/models" || true)"
echo "no-token status: $anon"
case "$anon" in 401|403) ;; *) echo "!! unauthenticated call was not rejected ($anon)"; exit 1 ;; esac
code="$(curl -sS -o "$OUT/models.json" -w '%{http_code}' \
  -H "Authorization: Bearer $HF_TOKEN" -H "X-Scale-Up-Timeout: 600" \
  "$HF_ENDPOINT_URL/v1/models" || true)"
echo "token status: $code"
[ "$code" = "200" ] || { echo "Endpoint not ready (HTTP $code)"; exit 1; }
python - <<'PY'
import json, os
ids = [m["id"] for m in json.load(open(f"results/real-model/{os.environ['RUN_ID']}/models.json"))["data"]]
print("served model ids:", ids)
assert os.environ["HF_API_MODEL"] in ids, "HF_API_MODEL not among served ids"
PY

echo "== G2: prepare requests and send one direct call"
python scripts/tier0_hf_run.py prep --run-id "$RUN_ID"
code="$(curl -sS -o "$OUT/raw_response.json" -w '%{http_code}' \
  -H "Authorization: Bearer $HF_TOKEN" -H "Content-Type: application/json" \
  --data-binary @"$OUT/raw_request.json" "$HF_ENDPOINT_URL/v1/chat/completions" || true)"
echo "direct call status: $code"
[ "$code" = "200" ] || { echo "Direct call failed"; exit 1; }
python - <<'PY'
import json, os
r = json.load(open(f"results/real-model/{os.environ['RUN_ID']}/raw_response.json"))
print("finish_reason:", r["choices"][0]["finish_reason"])
print("content present:", bool(r["choices"][0]["message"]["content"]))
PY

echo "== G3/G4: semantic fixture, 3 repeats through the unmodified adapter"
python scripts/tier0_hf_run.py run --run-id "$RUN_ID" --repeats 3

echo "== done: summary at $OUT/run_summary.json"
date -u +%FT%TZ > "$OUT/finished_utc.txt"
