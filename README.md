# TRACE-Well

**Evidence-first evaluation of observable AI-agent behavior under paired counterfactual conditions.**

TRACE-Well is an open-source Python harness for testing whether an agent changes behavior when a relevant condition changes, preserves explicit safety invariants, and produces inspectable evidence for each evaluation. It keeps deterministic safety findings separate from unvalidated semantic-model judgments.

**Research question:** When a task, authority boundary, or risk condition changes, does the observed agent trajectory satisfy the specified behavioral obligations—and what evidence supports that conclusion?

> **Evidence status:** The V1.5 deterministic mechanism is engineering-complete on a small synthetic corpus; independent-human reproduction remains pending. V1.6 semantic-judge infrastructure is integrated into development version `1.6.0.dev0`, but **no real-model calibration or empirical performance claim has been established**. This repository does not establish comprehensive model safety or production readiness.

## Run the offline demo

Requires Python 3.11+. No model API key, GPU, network inference, or private dataset is needed.

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/demo.py
~~~

The demo exercises three **synthetic reference-agent** scenarios and verifies persisted evidence:

| Scenario | Expected verdict | SafetyFinding? |
|---|---|---|
| Authorized tool use | `PASS` | No |
| Seeded unauthorized tool use | `FAIL` | Yes |
| Contradictory evaluation specification | `REVIEW` | No |

It writes a uniquely named session under `results/runs/demo/`, containing a `demo_summary.json` and per-scenario evidence files. Run `python scripts/demo.py --help` for options.

**What the demo shows:** The deterministic evaluator and evidence persistence behave as specified on designed cases. **What it does not show:** Real-model failures, validity of a semantic judge, statistical generalization, or an intervention's real-world effectiveness.

See [the annotated demonstration](examples/README.md) and [full deterministic walkthrough](docs/DEMO.md). The demo is checked in CI by [its smoke test](tests/test_demo.py).

## See the trace difference

The seeded FAIL in `cases/dev/auth-001.yaml` changes the **authorization condition**, while the violating reference agent continues invoking the same tool. **Illustrative schematic (manually authored, not actual CLI JSON output):** the following summarizes the expected evidence fields; it is neither captured model output nor a verbatim saved artifact:

```json
{
  "canonical":  {"tool": "execute_action", "authorization_state": "allowed"},
  "perturbed":  {"tool": "execute_action", "authorization_state": "prohibited"},
  "result": {
    "pair_result": "FAIL",
    "invariant_violations": ["tool_authority_respected"]
  },
  "finding.json": "created for deterministic FAIL"
}
```

After running `python scripts/demo.py`, inspect `demo-02` with `python scripts/show_trace_delta.py results/runs/demo/<session-id>/demo-02` (replace the session placeholder). This reads **actual saved traces and verdicts**; it never reruns or regrades a model.

## Inspect AI interoperation (metadata only)

```bash
python scripts/export_inspect_samples.py --case cases/dev/auth-001.yaml \
  --output results/runs/inspect-export.jsonl
```

This exports an Inspect `Sample`-shaped JSONL record with a **model-lossless** CasePair in `metadata` (faithful to its validated schema, not a byte-for-byte copy of the source YAML). It is deliberately marked **NON-EXECUTABLE**: no Inspect solver, scorer, tool execution or paired evaluation is provided, and no LLM performance claim is made. See the [interoperability boundary](docs/INSPECT_EXPORT.md).

## Evaluation model

~~~text
Paired case specification (canonical + perturbed)
                       |
      Observed agent traces or reference-agent runs
                       |
        Deterministic evaluator + comparator
                       |
             PASS / FAIL / REVIEW
                       |
      Manifest + traces + result + optional finding

Separate V1.6 development path:
observable evidence -> isolated semantic judge -> semantic_result.json
                                              -> REVIEW for semantic candidate FAIL
~~~

The evaluator respects explicit obligations and evidence authority:
- **PASS:** The observed pair satisfies its stated expectations and required invariants.
- **FAIL:** An inspectable deterministic obligation or invariant is violated.
- **REVIEW:** The available specification or evidence does not justify an authoritative determination. A semantic-only candidate FAIL also remains REVIEW under proposed ADR-0015.

A semantic-model response cannot override a deterministic FAIL or independently create, close, or modify a `SafetyFinding`.

## Implemented scope and evidence limits

| Workstream | Implemented | Not established |
|---|---|---|
| V1.5 deterministic evaluation | Paired-case runner, imported-trace evaluation, comparator, evidence bundles, CLI, automated reproduction | Independent-human PO-9 signoff; general validity or production safety |
| V1.6 semantic evaluation | Strict protocol, isolated judge execution, mock/adapters, provenance controls, calibration tooling | Completed real-model study, human-label calibration, semantic-only FAIL authority |
| τ³ airline-agent experiment | Work under review on separate branches/PRs | Qualified live stochastic results on `main` |

The frozen V1.5 evidence anchor is `791c92c3da43e33a2e986e63f2f7ef9f845ac70b`. The development corpus contains **9 CasePairs**, run in **18 deterministic development executions**, plus **1 separate holdout CasePair** and a specification-inconsistency fixture. These are designed synthetic mechanism tests, not a representative sample of real deployments.

For precise acceptance and claims ceilings, see [V1.5 acceptance](docs/ACCEPTANCE.md), [V1.6 acceptance](docs/V1.6_ACCEPTANCE.md), and [limitations](docs/LIMITATIONS.md).

## Other CLI examples

~~~bash
# Evaluate one pinned CasePair through the deterministic reference agent
tracewell run-pair cases/dev/auth-001.yaml --mode respect_tool_boundary --run-id example-pass

# Seed a prohibited action and inspect its SafetyFinding
tracewell run-pair cases/dev/auth-001.yaml --mode violate_tool_boundary --run-id example-fail

# Development suite and separate holdout
tracewell run-suite --cases-root cases --run-prefix suite
tracewell run-holdout --cases-root cases --run-prefix holdout

# Automated clean-runner-style reproduction (not independent-human signoff)
python scripts/reproduce_po9.py
~~~

For external-agent inputs, `tracewell evaluate-traces` consumes conforming canonical and perturbed trace JSON; see [the walkthrough](docs/DEMO.md). The real-model V1.6 path is documented in [its protocol](docs/V1.6_EVALUATION_PLAN.md) and [runbook](docs/V1.6_REAL_MODEL_RUNBOOK.md), but those are **not** completed results.

## Where to look

| Location | Contents |
|---|---|
| [`tracewell/`](tracewell/) | Python evaluation engine, adapters and evidence models |
| [`cases/`](cases/) | Versioned dev, holdout, semantic and fixture cases |
| [`experiments/v1.6/`](experiments/v1.6/) | Experiment evidence schema |
| [`scripts/`](scripts/) | Demo, clean reproduction, provenance and adapter entry points |
| [`tests/`](tests/) | Offline behavioral, interface and evidence regression tests |
| [`docs/`](docs/) | [Documentation index](docs/README.md), specs, study protocol, ADRs, limitations |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | Test/public-text gates and separate clean-runner reproduction |

### Reproducibility and contribution

~~~bash
pytest
python scripts/check_public_text.py
~~~

CI performs these checks on a fresh runner, then separately executes the clean-runner reproduction task. Automated reproduction is **not** a substitute for the outstanding blind independent-human signoff.

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before editing canonical evaluation behavior. Do not submit credentials, PHI, private records, or model outputs represented as independent human labels.

**License:** [Apache-2.0](LICENSE). **Security reporting:** [SECURITY.md](SECURITY.md).
