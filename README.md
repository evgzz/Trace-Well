# TRACE-Well

TRACE-Well V1.5 is a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Its deterministic MVP tests whether an agent makes a required behavioral change, preserves required invariants, and whether a configured mitigation survives both sides of the counterfactual using explicit, inspectable evidence.

## Current scope

V1.5 is a mechanism proof on controlled synthetic cases. It is not a model leaderboard, production safety platform, clinical decision-support system, release-governance engine, or statistical evaluation study.

The public claim ceiling is **prototype engineering evaluation evidence**. TRACE-Well V1.5 does not establish clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

## Relation to evaluation practice

TRACE-Well begins after an evaluation obligation has been specified. It presupposes rather than replaces error-analysis-driven criteria selection and domain-expert adjudication.

See [`docs/RELATION_TO_PRACTICE.md`](docs/RELATION_TO_PRACTICE.md).

## Repository status

The repository is currently being initialized for the V1.5 deterministic evaluation implementation. Architecture, evaluation, benchmark, reproducibility, and limitations documents are being integrated before core implementation.
