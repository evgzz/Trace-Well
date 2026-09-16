# TRACE-Well V1.5 — Deterministic Demo

This demo exercises the implemented V1.5 mechanism using the committed synthetic benchmark.

It does not demonstrate clinical validity, population performance, comprehensive safety, or production readiness.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## 1. Run one successful Tool Authority evaluation

```bash
tracewell run-pair \
  cases/dev/auth-001.yaml \
  --mode respect_tool_boundary \
  --run-id demo-auth-pass
```

Expected verdict:

```text
PASS
```

The generated evidence directory contains:

```text
manifest.json
canonical_trace.json
perturbed_trace.json
behavior_delta.json
```

## 2. Run the seeded Tool Authority failure

```bash
tracewell run-pair \
  cases/dev/auth-001.yaml \
  --mode violate_tool_boundary \
  --run-id demo-auth-fail
```

Expected verdict:

```text
FAIL
```

The evidence directory additionally contains a `finding.json` artifact.

## 3. Demonstrate invariant violation

```bash
tracewell run-pair \
  cases/dev/auth-002.yaml \
  --mode violate_tool_boundary \
  --run-id demo-invariant-fail
```

Expected:

- pair verdict `FAIL`;
- `tool_authority_respected` listed as an invariant violation;
- observable evidence references point to the prohibited tool call.

## 4. Demonstrate trajectory revision

```bash
tracewell run-pair \
  cases/dev/late-001.yaml \
  --mode respect_late_context \
  --run-id demo-late-pass
```

Expected verdict:

```text
PASS
```

Then run:

```bash
tracewell run-pair \
  cases/dev/late-001.yaml \
  --mode ignore_late_context \
  --run-id demo-late-fail
```

Expected verdict:

```text
FAIL
```

The evaluator derives `revised_after:risk-introduced` from observable ordered trace events.

## 5. Demonstrate global REVIEW for inconsistent specification

```bash
tracewell run-pair \
  cases/fixtures/po7-spec-inconsistent.yaml \
  --mode respect_context \
  --run-id demo-po7-review
```

Expected verdict:

```text
REVIEW
```

The observable action transition itself satisfies the CasePair expectation, but the perturbed EvaluationContract conflicts with that expectation. Global specification inconsistency therefore outranks behavioral judgment.

## 6. Run the full development suite

```bash
tracewell run-suite \
  --cases-root cases \
  --run-prefix demo-suite
```

The committed inventory currently contains:

```text
9 distinct development CasePairs
18 deterministic development executions
9 expected PASS directions
9 expected seeded FAIL directions
```

Agent modes are run configuration and do not increase the CasePair count.

## 7. Run the explicit holdout

```bash
tracewell run-holdout \
  --cases-root cases \
  --run-prefix demo-holdout
```

The holdout is intentionally excluded from `run-suite`.

## 8. Re-evaluate imported traces

Given previously persisted conforming traces:

```bash
tracewell evaluate-traces \
  canonical_trace.json \
  perturbed_trace.json \
  cases/dev/auth-001.yaml \
  --run-id demo-imported
```

Imported traces use the same deterministic evaluator and BehaviorDeltaComparator as built-in execution.

## 9. Repository gates

```bash
pytest
python scripts/check_public_text.py
```

Both must pass in the credential-free base environment.

## Interpretation

The demo proves the deterministic evaluation mechanism on designed synthetic cases.

It does not prove that the benchmark represents the frequency, severity, or completeness of failures in a real deployed system.
