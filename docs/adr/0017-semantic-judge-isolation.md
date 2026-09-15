# ADR-0017 — Isolated Semantic-Judge Execution Contract

**Status:** Proposed  
**Spec:** Future semantic phase

## Context

Some future obligations may require semantic judgment that cannot be resolved mechanically. That capability must not contaminate the deterministic V1.5 core or be treated as ground truth.

## Decision

If implemented in a future phase, `semantic_judge` should use a structured JSON boundary, with out-of-process execution preferred for self-hosted judges:

```text
TRACE-Well core
→ JudgeRequest JSON
→ isolated judge process/service
→ JudgeResponse JSON
→ evaluator
→ PASS / FAIL / REVIEW
```

Open-weight, hosted, local-service, or subprocess execution are runtime choices, not distinct architecture families.

Judge provenance may include execution mode, model/revision identity, weights digest where available, inference engine/version, quantization, generation settings, and judge-prompt version.

A semantic judge:

- is not ground truth;
- requires validation against human labels before consequential use;
- cannot erase an established deterministic failure;
- is not required for V1.5 acceptance.

## Consequences

Heavy inference dependencies stay outside the core environment. Future judge implementations can vary while retaining a stable capability contract.

## Alternatives rejected

- Making one model/provider part of the tracked architecture: rejected as unnecessarily specific.
- Mandatory in-process inference: rejected because it expands the core dependency/runtime boundary.
- Treating semantic judgment as authoritative ground truth: rejected.

---

**Related ADRs:** 0004, 0015, 0016, 0019
