# TRACE-Well

TRACE-Well V1.5 is a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Its deterministic MVP tests whether an agent makes a required behavioral change, preserves required invariants, and whether a configured mitigation survives both sides of the counterfactual using explicit, inspectable evidence.

## Current scope

V1.5 is a mechanism proof on controlled synthetic cases. It is not a model leaderboard, production safety platform, clinical decision-support system, release-governance engine, or statistical evaluation study.

The public claim ceiling is **prototype engineering evaluation evidence**. TRACE-Well V1.5 does not establish clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

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

## Relation to evaluation practice

TRACE-Well begins after an evaluation obligation has been specified. It presupposes rather than replaces error-analysis-driven criteria selection and domain-expert adjudication.

See [`docs/RELATION_TO_PRACTICE.md`](docs/RELATION_TO_PRACTICE.md).

## Phase 0 controls

The repository includes:

- `AGENTS.md`
- `pyproject.toml`
- `scripts/check_public_text.py`
- `tests/test_dependency_boundary.py`
- `.github/workflows/ci.yml`
- `.gitignore`
- Apache-2.0 `LICENSE`

Before implementation changes are accepted:

```bash
pytest
python scripts/check_public_text.py
```

must pass in the credential-free base environment.

## Repository status

The V1.5 canonical specification and Phase-0 repository controls are integrated. Core deterministic implementation begins only after the latest `main` CI run is green.
