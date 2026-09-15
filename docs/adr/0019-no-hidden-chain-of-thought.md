# ADR-0019 — No Hidden Chain-of-Thought Capture

**Status:** Accepted  
**Spec:** `docs/ARCHITECTURE.md`, `docs/LIMITATIONS.md`

## Context

TRACE-Well evaluates observable system behavior. Hidden chain-of-thought is neither necessary nor appropriate as a V1.5 evidence requirement.

## Decision

TRACE-Well must never request, capture, persist, require, or evaluate hidden chain-of-thought.

Observable rationale emitted as normal system output may be stored as output evidence, but it is not privileged reasoning provenance and cannot substitute for observable action/tool/context evidence.

## Consequences

- Traces remain limited to observable execution events.
- Evaluation focuses on behavior rather than inaccessible internal reasoning.
- Generated explanations are treated as ordinary outputs, not causal proof.

## Alternatives rejected

- Requiring hidden reasoning traces for evaluation: rejected.
- Treating self-reported rationale as internal ground truth: rejected.

---

**Related ADRs:** 0004, 0017
