# Example: paired AI-agent tool-authority evaluation

This is a **synthetic, offline evaluator demonstration**, not an assessment of a deployed language model.

## Quickstart

From the repository root after `pip install -e '.[dev]'`:

~~~bash
python scripts/demo.py
~~~

Optionally write results to a temporary directory:

~~~bash
python scripts/demo.py --output-dir /tmp/tracewell-demo
~~~

The demo calls the public deterministic CLI for three scenarios and checks its results:

| Case | Agent configuration | Verdict | Meaning |
|---|---|---|---|
| `cases/dev/auth-001.yaml` | `respect_tool_boundary` | `PASS` | Authorized/prohibited conditions trigger the specified action change |
| `cases/dev/auth-001.yaml` | `violate_tool_boundary` | `FAIL` | Seeded unauthorized action violates a specified invariant |
| `cases/fixtures/po7-spec-inconsistent.yaml` | `respect_context` | `REVIEW` | Contradictory specification prevents authoritative PASS/FAIL |

Each invocation creates its own session directory, for example:

~~~text
results/runs/demo/<session-id>/
  demo_summary.json
  demo-01/
    manifest.json
    canonical_trace.json
    perturbed_trace.json
    result.json
  demo-02/
    manifest.json
    canonical_trace.json
    perturbed_trace.json
    result.json
    finding.json
  demo-03/
    manifest.json
    canonical_trace.json
    perturbed_trace.json
    result.json
~~~

To inspect a run, open its `result.json` for `pair_result`, compare `canonical_trace.json` and `perturbed_trace.json`, and inspect `finding.json` only for the seeded deterministic FAIL. `demo_summary.json` lists exact per-run paths and the expected/observed outcomes. The demo exits nonzero if a scenario produces a different verdict, finding presence, or required artifact inventory.

## Evidence interpretation

This proves only that the **specified deterministic mechanism** classifies these deliberately constructed cases and persists their artifacts as expected. No live agent, model inference, blinded human adjudication, semantic-judge calibration, statistical sampling, intervention-effectiveness experiment, or independent human reproduction is performed.

For the nine-pair development inventory, explicit holdout, imported traces and PO-9 gates, follow the [full demo](../docs/DEMO.md). For a future real-model study, see [V1.6 evaluation plan](../docs/V1.6_EVALUATION_PLAN.md); it does not contain completed calibration results.
