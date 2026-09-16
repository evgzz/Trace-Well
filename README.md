# TRACE-Well

TRACE-Well V1.5 is a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Its deterministic MVP tests whether an agent makes a required behavioral change, preserves required invariants, and whether a configured mitigation survives both sides of the counterfactual using explicit, inspectable evidence.

## Release status

| Gate | Status |
|---|---|
| Engineering / repository **Done** | ✅ Complete |
| Automated PO-1–PO-11 evidence | ✅ Complete |
| PO-9 clean-runner reproduction on a fresh CI runner | ✅ Complete |
| PO-9 blind independent-human reproduction from public documentation alone | ⬜ Pending |
| V1.5 **Fully Proven** | ⬜ Blocked only by the independent-human PO-9 signoff and operator self-attestation |

### What remains before V1.5 can be described as fully Proven

One **eligible, previously unexposed human operator** must execute [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) from a clean checkout using only the public repository and ordinary public documentation for standard tools.

The operator must:

- have no prior exposure to TRACE-Well design discussions, private planning, unpublished guidance, implementation/review work, or preparation of the reproduction procedure;
- receive no TRACE-Well-specific clarification, walkthrough, or side-channel help from the author or another informed project participant during the attempt;
- reproduce the required PASS, FAIL, REVIEW, digest-invariance, development-suite, and holdout results;
- personally provide or affirmatively adopt the required first-person eligibility/no-side-channel self-attestation.

If the operator needs TRACE-Well-specific clarification, the attempt stops and the blocker is treated as a **documentation/repository-sufficiency defect**. The public material must be corrected and the reproduction re-attempted from a clean checkout; the operator must not be privately unblocked and allowed to continue the same signoff attempt.

See [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) for the authoritative Proven/Done gate and [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) for the operator protocol.

> **Do not describe V1.5 as fully Proven until that independent-human signoff and operator self-attestation have actually been recorded.**

## Current scope

V1.5 is a mechanism proof on controlled synthetic cases. It is not a model leaderboard, production safety platform, clinical decision-support system, release-governance engine, or statistical evaluation study.

The public claim ceiling is **prototype engineering evaluation evidence**. TRACE-Well V1.5 does not establish clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Requires Python 3.11 or newer.

## Implemented commands

```bash
tracewell version
tracewell run-pair cases/dev/auth-001.yaml --mode respect_tool_boundary --run-id example-pass
tracewell evaluate-traces canonical_trace.json perturbed_trace.json cases/dev/auth-001.yaml --run-id imported-example
tracewell run-suite --cases-root cases --run-prefix suite
tracewell run-holdout --cases-root cases --run-prefix holdout
```

The package and CLI version are `1.5.0`.

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

## Evidence and reproducibility

Built-in and imported-trace runs persist inspectable evidence bundles containing:

```text
manifest.json
canonical_trace.json
perturbed_trace.json
result.json
```

A deterministic `FAIL` additionally persists `finding.json`. A global `REVIEW` does not create a normal SafetyFinding.

PO-9 automated clean-runner reproduction is implemented by:

```bash
python scripts/reproduce_po9.py
```

It writes:

```text
results/reproduction/po9-reproduction-report.json
```

The CI artifact report explicitly records that it is an automated clean runner and **not** an independent-human signoff.

## Canonical specification

Read the repository in this order:

1. [`docs/MVP_SCOPE.md`](docs/MVP_SCOPE.md) — scope, non-goals, claims ceiling, Proven vs Done.
2. [`docs/PRD.md`](docs/PRD.md) — PO-1 through PO-11.
3. [`docs/PO_ADR_MAP.md`](docs/PO_ADR_MAP.md) — proof-to-decision traceability.
4. [`docs/adr/README.md`](docs/adr/README.md) — authoritative ADR registry.
5. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — canonical schemas, capabilities, artifact identity, run provenance.
6. [`docs/EVALUATION_SPEC.md`](docs/EVALUATION_SPEC.md) — deterministic comparator and verdict precedence.
7. [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) — distinct CasePair design, controls, holdout, Proven coverage.
8. [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — PO-9 end-to-end semantics.
9. [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — interpretation and evidence limits.
10. [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) — auditable PO-1 through PO-11 completion matrix and release gate.
11. [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) — blind independent-human PO-9 signoff protocol.

## Relation to evaluation practice

TRACE-Well begins after an evaluation obligation has been specified. It presupposes rather than replaces error-analysis-driven criteria selection and domain-expert adjudication.

See [`docs/RELATION_TO_PRACTICE.md`](docs/RELATION_TO_PRACTICE.md).

## Repository gates

Changes are gated by two separate CI jobs:

1. **Deterministic V1.5 Gate** — fresh checkout, Python 3.11 setup, dependency installation, `pytest`, and `python scripts/check_public_text.py`.
2. **PO-9 Clean-Runner Reproduction** — starts only after the deterministic gate succeeds, uses a separate fresh runner, executes `python scripts/reproduce_po9.py`, and uploads the `po9-reproduction-report` artifact.

The clean-runner result does **not** substitute for the blind independent-human signoff described above.

## Current status

The canonical specification, deterministic execution path, benchmark corpus, evidence persistence, external-trace path, paired mitigation verification, CLI, automated proof coverage, and automated clean-runner reproduction are implemented and passing.

The repository is **Done**. Full **Proven** status remains blocked only by the blind independent-human PO-9 reproduction and operator self-attestation described at the top of this README.
