# TRACE-Well — Roadmap

This file holds work intentionally outside the V1.5 deterministic MVP unless a future release explicitly promotes it into scope.

## Deferred evaluation capabilities

- validated semantic-judge execution boundary from ADR-0017;
- semantic FAIL propagation policy from ADR-0015;
- judge calibration against human labels;
- multi-judge disagreement handling;
- stochastic model repetitions and seed-variance analysis;
- quantitative reliability estimates on sufficiently powered datasets;
- larger error-analysis-derived corpora;
- clinician/domain-expert adjudication workflows;
- adversarial or adaptive simulators.

## Deferred execution integrations

- hosted-model adapters;
- local-model adapters;
- broader agent-framework integrations;
- production retrieval/connectors;
- live side-effecting tool integrations.

## Deferred product capabilities

- interactive review UI;
- multi-user evidence store;
- workflow approvals;
- release-governance integration;
- residual-risk management;
- dashboards and longitudinal trend analysis.

## Deferred production engineering

- database-backed persistence;
- enterprise IAM;
- multi-tenant isolation;
- high availability;
- production monitoring and incident response;
- scale/performance certification.

## Admission rule

A roadmap item enters a future release only through an explicit scope/PRD change and, where load-bearing, a new ADR.

V1.5 should not absorb roadmap work merely because it is useful.
