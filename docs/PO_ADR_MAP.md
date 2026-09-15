# TRACE-Well V1.5 — Proof Obligation to ADR Map

## Enabling rule

An ADR enables a proof obligation when that obligation cannot be demonstrated with its required semantics without the decision captured by that ADR, including fixture production and verdict logic.

## PO → ADR

| Proof obligation | Enabling ADRs |
|---|---|
| PO-1 | 0001, 0006, 0007, 0014 |
| PO-2 | 0001, 0005, 0006, 0007, 0014 |
| PO-3 | 0001, 0005, 0006 |
| PO-4 | 0001, 0014 |
| PO-5 | 0014 |
| PO-6 | 0008, 0014 |
| PO-7 | 0002, 0005 |
| PO-8 | 0009 |
| PO-9 | 0010, 0020 |
| PO-10 | 0016 |
| PO-11 | 0012, 0018 |

## ADR → PO transpose

| ADR | Enabled POs |
|---|---|
| 0001 | PO-1, PO-2, PO-3, PO-4 |
| 0002 | PO-7 |
| 0005 | PO-2, PO-3, PO-7 |
| 0006 | PO-1, PO-2, PO-3 |
| 0007 | PO-1, PO-2 |
| 0008 | PO-6 |
| 0009 | PO-8 |
| 0010 | PO-9 |
| 0012 | PO-11 |
| 0014 | PO-1, PO-2, PO-4, PO-5, PO-6 |
| 0016 | PO-10 |
| 0018 | PO-11 |
| 0020 | PO-9 |

## Constraint ADRs

These are load-bearing but are not direct PO enablers:

- 0003 — deterministic reference agent + provider-independent execution boundary;
- 0004 — deterministic-first evaluator; semantic judge not ground truth;
- 0011 — no formal statistics / claims ceiling;
- 0013 — Apache-2.0 distribution license;
- 0019 — no hidden chain-of-thought capture.

## Deferred ADRs

- 0015 — semantic FAIL propagation versus REVIEW — Proposed / future semantic phase.
- 0017 — isolated semantic-judge execution contract — Proposed / future semantic phase.

## Cross-layer example

```text
PO-2
→ ADRs 0001 / 0005 / 0006 / 0007 / 0014
→ architecture objects and deterministic reference behavior
→ comparator test
→ persisted evidence
```

Authority flows downward. ADRs explain *why* requirements are implemented a certain way; they do not invent product requirements.
