# TRACE-Well Architecture Decision Records

This index is authoritative for ADR number, title, status, and primary specification reference.

## Status model

`Proposed` → `Accepted` → `Superseded-by-NNNN` / `Deprecated`

For an Accepted ADR, the Decision section is immutable. Replace a decision by superseding it with a new ADR rather than rewriting history.

Not every historical/indexed decision has a standalone file in this repository snapshot. Do not fabricate historical ADR files merely to make every index row clickable.

## Registry

| ADR | Title | Status | Primary spec reference |
|---:|---|---|---|
| 0001 | Paired/counterfactual behavioral-delta primitive | Accepted | PRD PO-1–PO-4 |
| 0002 | REVIEW never silently becomes PASS | Accepted | EVALUATION_SPEC |
| 0003 | Deterministic reference agent and provider-independent execution | Accepted | ARCHITECTURE |
| 0004 | Deterministic-first evaluation; semantic judge is not ground truth | Accepted | EVALUATION_SPEC |
| 0005 | CasePair is authoritative for cross-condition expectations | Accepted | ARCHITECTURE |
| 0006 | Construct-keyed ConditionEvaluation | Accepted | ARCHITECTURE |
| 0007 | ExpectedChange supports categorical JSON-scalar transitions | Accepted | ARCHITECTURE |
| 0008 | Fixed scripted multi-turn; no adaptive simulator in V1.5 | Accepted | BENCHMARK_DESIGN |
| 0009 | Paired mitigation verification reruns both conditions | Accepted | EVALUATION_SPEC |
| 0010 | Persist explicit reproducibility configuration | Accepted | REPRODUCIBILITY |
| 0011 | No formal statistics; mechanism-proof claims ceiling | Accepted | MVP_SCOPE |
| 0012 | Public-repository neutrality: generic scanner + optional private augmentation | Accepted | AGENTS / LIMITATIONS |
| 0013 | Apache-2.0 license | Accepted | LICENSE |
| 0014 | Explicit deterministic reference-agent behavior taxonomy | Accepted | ARCHITECTURE / BENCHMARK_DESIGN |
| 0015 | Semantic FAIL propagation versus REVIEW | Proposed | Future semantic phase |
| 0016 | Build/buy boundary and capability seams with external trace input | Accepted | ARCHITECTURE |
| 0017 | Isolated semantic-judge execution contract | Proposed | Future semantic phase |
| 0018 | CI and publication gating | Accepted | AGENTS / CI |
| 0019 | No hidden chain-of-thought capture | Accepted | ARCHITECTURE / LIMITATIONS |
| 0020 | Canonical artifact normalization | Accepted | ARCHITECTURE / REPRODUCIBILITY |

## Full ADR files in this snapshot

- `0014-deterministic-reference-agent-taxonomy.md`
- `0016-build-buy-capability-seams.md`
- `0017-semantic-judge-isolation.md` — Proposed
- `0018-ci-publication-gating.md`
- `0019-no-hidden-chain-of-thought.md`
- `0020-canonical-artifact-normalization.md`
