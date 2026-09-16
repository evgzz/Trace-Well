# TRACE-Well

TRACE-Well V1.5 is a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Its deterministic MVP tests whether an agent makes a required behavioral change, preserves required invariants, and whether a configured mitigation survives both sides of the counterfactual using explicit, inspectable evidence.

## Current scope

V1.5 is a mechanism proof on controlled synthetic cases. It is not a model leaderboard, production safety platform, clinical decision-support system, release-governance engine, or statistical evaluation study.

The public claim ceiling is **prototype engineering evaluation evidence**. TRACE-Well V1.5 does not establish clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Implemented commands

```bash
tracewell version
tracewell run-pair cases/dev/auth-001.yaml --mode respect_tool_boundary --run-id example-pass
tracewell evaluate-traces canonical_trace.json perturbed_trace.json cases/dev/auth-001.yaml --run-id imported-example
tracewell run-suite --cases-root cases --run-prefix suite
tracewell run-holdout --cases-root cases --run-prefix holdout
```

See [`docs/DEMO.md`](docs/DEMO.md) for the deterministic walkthrough.

## Benchmark corpus

The committed V1.5 corpus currently contains:

- 9 distinct development CasePairs;
- 18 deterministic development executions;
- 9 expected PASS directions;
- 9 expected seeded FAIL directions;
- 1 separately executed holdout CasePair;
- 1 dedicated inconsistent-specification fixture for PO-7 `REVIEW`.

Agent modes are execution configuration; they do not create additional CasePair identities.

## Canonical specification

Read the repository in this order:

1. [`docs/MVP_SCOPE.md`](docs/MVP_SCOPE.md) — scope, non-goals, claims ceiling, Proven vs Done.
2. [`docs/PRD.md`](docs/PRD.md) — PO-1 through PO-11.
3. [`docs/PO_ADR_MAP.md`](docs/PO_ADR_MAP.md) — proof-to-decision traceability.
4. [`docs/adr/README.md`](docs/adr/README.md) — authoritative ADR registry.
5. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — canonical schemas, capabilities, artifact identity, run provenance.
6. [`docs/EVALUATION_SPEC.md`](docs/EVALUATION_SPEC.md) — deterministic comparator and verdict precedence.
7. [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) — distinct CasePair design, controls, holdout, Proven coverage.
8. [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — PO-9 end-to-end.
9. [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — interpretation and evidence limits.
10. [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) — auditable PO-1 through PO-11 completion matrix.

## Relation to evaluation practice

TRACE-Well begins after an evaluation obligation has been specified. It presupposes rather than replaces error-analysis-driven criteria selection and domain-expert adjudication.

See [`docs/RELATION_TO_PRACTICE.md`](docs/RELATION_TO_PRACTICE.md).

## Repository gates

Before changes are accepted:

```bash
pytest
python scripts/check_public_text.py
```

must pass in the credential-free base environment.

## Current status

The canonical specification, deterministic execution path, benchmark corpus, evidence persistence, external-trace path, paired mitigation verification, and CLI are implemented and covered by CI.

Automated proof coverage exists for PO-1 through PO-11. **PO-9 still requires the documented independent-operator clean-clone reproduction signoff before the repository should be described as fully Proven.**
