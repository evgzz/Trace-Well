#!/usr/bin/env bash
# Tier-0 hosted-endpoint run for GitHub Codespaces (transport_only evidence).
# Requires: Codespaces secret HF_TOKEN, a running or scaled-to-zero dedicated
# endpoint, repo root as cwd. The endpoint is never resumed by this script.
# After admission succeeds it pauses the endpoint on exit unless TIER0_PAUSE_ON_EXIT=0.
set -euo pipefail

: "${HF_TOKEN:?Set HF_TOKEN as a Codespaces secret, then restart the codespace}"
: "${HF_ENDPOINT_URL:?export HF_ENDPOINT_URL=https://<endpoint-host>}"
: "${HF_ENDPOINT_NAME:?set HF_ENDPOINT_NAME to your endpoint name}"
: "${HF_REVISION:?set HF_REVISION to the approved immutable model revision}"
HF_ENDPOINT_NAMESPACE="${HF_ENDPOINT_NAMESPACE:-}"
export HF_API_MODEL="${HF_API_MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"
export HF_ENGINE="${HF_ENGINE:-vllm}"
export RUN_ID="${RUN_ID:-tier0-qwen-hf-001}"
export HF_REVISION
TIER0_PAUSE_ON_EXIT="${TIER0_PAUSE_ON_EXIT:-1}"
TIER0_PAUSE_CONFIRM_SECONDS="${TIER0_PAUSE_CONFIRM_SECONDS:-300}"
TIER0_PAUSE_POLL_SECONDS="${TIER0_PAUSE_POLL_SECONDS:-5}"
# End-to-end bound on the pause command, including a blocked control-plane call.
TIER0_PAUSE_COMMAND_SECONDS="${TIER0_PAUSE_COMMAND_SECONDS:-420}"

# Per-request limits for the G1/G2 curl calls. The wake-up asks the endpoint
# to scale up for up to 600 s, so the request limit must exceed that.
TIER0_CURL_CONNECT_SECONDS="${TIER0_CURL_CONNECT_SECONDS:-30}"
TIER0_CURL_MAX_SECONDS="${TIER0_CURL_MAX_SECONDS:-660}"
SCALE_UP_TIMEOUT_SECONDS=600

# Checked before admission: a bad value found only at cleanup would leave the
# endpoint running. GNU timeout treats "inf" and "0" as no limit, and an
# overlong decimal converts to inf in Python and awk, so accept only short
# positive decimals: at most 5 integer and 3 fractional digits (< 100000 s).
positive_seconds() {
  [[ "$2" =~ ^[0-9]{1,5}([.][0-9]{1,3})?$ ]] && ! [[ "$2" =~ ^0+([.]0+)?$ ]] \
    || { echo "$1 must be a positive number of seconds below 100000 (got '$2')" >&2; exit 2; }
}
must_exceed() {
  awk -v a="$2" -v b="$3" 'BEGIN { exit !(a > b) }' \
    || { echo "$1 must exceed $4" >&2; exit 2; }
}
positive_seconds TIER0_PAUSE_CONFIRM_SECONDS "$TIER0_PAUSE_CONFIRM_SECONDS"
positive_seconds TIER0_PAUSE_POLL_SECONDS "$TIER0_PAUSE_POLL_SECONDS"
positive_seconds TIER0_PAUSE_COMMAND_SECONDS "$TIER0_PAUSE_COMMAND_SECONDS"
positive_seconds TIER0_CURL_CONNECT_SECONDS "$TIER0_CURL_CONNECT_SECONDS"
positive_seconds TIER0_CURL_MAX_SECONDS "$TIER0_CURL_MAX_SECONDS"
must_exceed TIER0_PAUSE_COMMAND_SECONDS "$TIER0_PAUSE_COMMAND_SECONDS" "$TIER0_PAUSE_CONFIRM_SECONDS" TIER0_PAUSE_CONFIRM_SECONDS
must_exceed TIER0_CURL_MAX_SECONDS "$TIER0_CURL_MAX_SECONDS" "$SCALE_UP_TIMEOUT_SECONDS" "the ${SCALE_UP_TIMEOUT_SECONDS}s scale-up timeout"
TIER0_REPEATS="${TIER0_REPEATS:-3}"
[[ "$TIER0_REPEATS" =~ ^[0-9]{1,2}$ ]] && (( 10#$TIER0_REPEATS >= 1 && 10#$TIER0_REPEATS <= 10 )) \
  || { echo "TIER0_REPEATS must be an integer from 1 to 10 (got '$TIER0_REPEATS')" >&2; exit 2; }
TIER0_REPEATS=$((10#$TIER0_REPEATS))
PAUSE_KILL_GRACE_SECONDS=10
OUT="${TIER0_OUT_DIR:-results/real-model/${RUN_ID}}"
export OUT
mkdir -p "$OUT"

# Budget report before anything else runs. The total covers the bounded stages
# only; it is not a guaranteed maximum run time or cost cap. The operator must
# acknowledge this exact report (commit, repeats, limits) by its budget id.
commit="$(git rev-parse HEAD)"
dirty=""
[ -z "$(git status --porcelain)" ] || dirty="--worktree-dirty"
python scripts/tier0_admission.py budget --commit "$commit" $dirty \
  --repeats "$TIER0_REPEATS" \
  --curl-connect-seconds "$TIER0_CURL_CONNECT_SECONDS" --curl-max-seconds "$TIER0_CURL_MAX_SECONDS" \
  --pause-confirm-seconds "$TIER0_PAUSE_CONFIRM_SECONDS" --pause-poll-seconds "$TIER0_PAUSE_POLL_SECONDS" \
  --pause-command-seconds "$TIER0_PAUSE_COMMAND_SECONDS" --pause-kill-grace-seconds "$PAUSE_KILL_GRACE_SECONDS" \
  --json-out "$OUT/budget_report.json" \
  || { echo "Could not compute the run budget; stopping before admission." >&2; exit 2; }
budget_id="$(python -c 'import json, sys; print(json.load(open(sys.argv[1]))["budget_id"])' "$OUT/budget_report.json")"
if [ "${TIER0_BUDGET_ACK:-}" != "$budget_id" ]; then
  echo "Budget not acknowledged. Review the report above, then rerun with TIER0_BUDGET_ACK=$budget_id" >&2
  exit 2
fi

# Set only after admission succeeds; cleanup acts on this identity alone.
ADMITTED_NAME=""
ADMITTED_NAMESPACE=""

cleanup() {
  status=$?
  if [ -n "$ADMITTED_NAME" ] && [ "$TIER0_PAUSE_ON_EXIT" = "1" ]; then
    echo "== cleanup: pausing admitted endpoint $ADMITTED_NAME"
    if ! timeout --kill-after="$PAUSE_KILL_GRACE_SECONDS" "$TIER0_PAUSE_COMMAND_SECONDS" \
      python scripts/tier0_admission.py pause --endpoint-name "$ADMITTED_NAME" \
      ${ADMITTED_NAMESPACE:+--namespace "$ADMITTED_NAMESPACE"} \
      --confirm-timeout "$TIER0_PAUSE_CONFIRM_SECONDS" \
      --poll-interval "$TIER0_PAUSE_POLL_SECONDS" \
      > "$OUT/endpoint_state_after.txt"; then
      echo "!! PAUSE NOT CONFIRMED: pause it manually in the dashboard NOW" >&2
      # Kept apart from inference results; a clean run must not report success.
      echo "$(date -u +%FT%TZ) pause failed for $ADMITTED_NAME" > "$OUT/cleanup_failed.txt"
      [ "$status" -ne 0 ] || status=3
    fi
  elif [ -z "$ADMITTED_NAME" ]; then
    echo "== cleanup: endpoint was not admitted; leaving its state unchanged"
  fi
  echo "== exit status $status. Revoke the run token after confirming 'paused'."
  exit $status
}
trap cleanup EXIT

# Calls to the inference host: no user curl config, HTTPS only, no redirects,
# connect and total-time limits, explicit status checks by the caller.
curl_safe() {
  curl -q --proto '=https' --max-redirs 0 -sS \
    --connect-timeout "$TIER0_CURL_CONNECT_SECONDS" --max-time "$TIER0_CURL_MAX_SECONDS" "$@"
}

echo "== G0: branch, ignore rule, baseline"
grep -qx "results/real-model/" .gitignore || { echo "Add 'results/real-model/' to .gitignore first"; exit 1; }
# TIER0_SKIP_SETUP=1 skips these setup gates (used by the offline tests). It is
# not a security boundary: admission and host binding below always run.
if [ "${TIER0_SKIP_SETUP:-0}" != "1" ]; then
  branch="$(git branch --show-current)"
  if [ "$branch" = "main" ]; then echo "Refusing to run on main"; exit 1; fi
  python -m pip install -q -e '.[dev]' huggingface_hub
  pytest -q
  python scripts/check_public_text.py
fi

echo "== G1: endpoint admission (control plane only, no inference)"
date -u +%FT%TZ > "$OUT/started_utc.txt"
admission="$(python scripts/tier0_admission.py admit \
  --endpoint-name "$HF_ENDPOINT_NAME" \
  ${HF_ENDPOINT_NAMESPACE:+--namespace "$HF_ENDPOINT_NAMESPACE"} \
  --configured-url "$HF_ENDPOINT_URL" \
  --expected-revision "$HF_REVISION")" \
  || { echo "Endpoint admission failed; no token was sent to the inference host." >&2; exit 1; }
printf '%s\n' "$admission" > "$OUT/admission.json"
field() { printf '%s' "$admission" | python -c 'import json, sys; print(json.load(sys.stdin)[sys.argv[1]])' "$1"; }
HF_EXPECTED_HOST="$(field expected_host)"
HF_ENDPOINT_URL="$(field origin)"
ADMITTED_NAMESPACE="$(field namespace)"
ADMITTED_NAME="$(field endpoint_name)"
export HF_EXPECTED_HOST HF_ENDPOINT_URL
echo "admitted: $ADMITTED_NAME state=$(field status) host=$HF_EXPECTED_HOST"
field status > "$OUT/endpoint_state_before.txt"

echo "== G1: auth enforcement (expect 401/403) and wake-up (expect 200)"
anon="$(curl_safe -o /dev/null -w '%{http_code}' "$HF_ENDPOINT_URL/v1/models")" \
  || { echo "Unauthenticated probe failed; stopping." >&2; exit 1; }
echo "no-token status: $anon"
case "$anon" in 401|403) ;; *) echo "!! unauthenticated call was not rejected ($anon)"; exit 1 ;; esac
code="$(curl_safe --fail-with-body -o "$OUT/models.json" -w '%{http_code}' \
  -H "Authorization: Bearer $HF_TOKEN" -H "X-Scale-Up-Timeout: $SCALE_UP_TIMEOUT_SECONDS" \
  "$HF_ENDPOINT_URL/v1/models")" \
  || { echo "Authenticated wake-up request failed; stopping." >&2; exit 1; }
echo "token status: $code"
[ "$code" = "200" ] || { echo "Endpoint not ready (HTTP $code)"; exit 1; }
python - <<'PY'
import json, os
ids = [m["id"] for m in json.load(open(os.path.join(os.environ["OUT"], "models.json")))["data"]]
print("served model ids:", ids)
assert os.environ["HF_API_MODEL"] in ids, "HF_API_MODEL not among served ids"
PY

echo "== G2: prepare requests and send one direct call"
python scripts/tier0_hf_run.py prep --run-id "$RUN_ID" --out "$OUT"
code="$(curl_safe --fail-with-body -o "$OUT/raw_response.json" -w '%{http_code}' \
  -H "Authorization: Bearer $HF_TOKEN" -H "Content-Type: application/json" \
  --data-binary @"$OUT/raw_request.json" "$HF_ENDPOINT_URL/v1/chat/completions")" \
  || { echo "Direct inference request failed; stopping." >&2; exit 1; }
echo "direct call status: $code"
[ "$code" = "200" ] || { echo "Direct call failed (HTTP $code)"; exit 1; }
python - <<'PY'
import json, os
r = json.load(open(os.path.join(os.environ["OUT"], "raw_response.json")))
print("finish_reason:", r["choices"][0]["finish_reason"])
print("content present:", bool(r["choices"][0]["message"]["content"]))
PY

echo "== G3/G4: semantic fixture, $TIER0_REPEATS repeats through the adapter"
python scripts/tier0_hf_run.py run --run-id "$RUN_ID" --out "$OUT" --repeats "$TIER0_REPEATS"

echo "== done: summary at $OUT/run_summary.json"
date -u +%FT%TZ > "$OUT/finished_utc.txt"
