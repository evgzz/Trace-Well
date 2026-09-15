# ADR-0014 — Explicit Deterministic Reference-Agent Behavior Taxonomy

**Status:** Accepted  
**Spec:** `docs/ARCHITECTURE.md`, `docs/BENCHMARK_DESIGN.md`

## Context

V1.5 must prove evaluator mechanics without depending on external model credentials or nondeterministic inference. The benchmark also needs explicit positive and seeded-failure directions across all four scenario families.

## Decision

The deterministic reference agent exposes explicit behavior modes:

- `respect_context`
- `ignore_context`
- `detect_contradiction`
- `ignore_contradiction`
- `respect_tool_boundary`
- `violate_tool_boundary`
- `respect_late_context`
- `ignore_late_context`
- `always_escalate`

The selected mode is execution configuration and is persisted as `agent_mode` in run provenance.

`agent_mode` is not CasePair identity and is not `agent_version`.

The same CasePair may therefore be executed under multiple modes to demonstrate success, underreaction, overreaction, invariant violation, or failure-to-revise without inflating the CasePair count.

## Consequences

- V1.5 acceptance remains credential-free and deterministic.
- Seeded failure directions are explicit and reproducible.
- CasePair specifications remain separate from run configuration.
- The reference agent validates evaluator mechanics, not production-model realism or prevalence.

## Alternatives rejected

- Using an external model as the acceptance agent: rejected because it introduces credentials and nondeterminism into the core proof.
- Encoding success/failure modes as separate CasePairs: rejected because it conflates benchmark specification with execution configuration.
- Inferring arbitrary semantic contradiction or risk: rejected for V1.5 because deterministic fixture state is required.

---

**Implements:** PO-1, PO-2, PO-4, PO-5, PO-6  
**Related ADRs:** 0003, 0004, 0008, 0010
