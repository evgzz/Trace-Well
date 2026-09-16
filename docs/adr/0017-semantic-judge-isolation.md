# ADR-0017 — Isolated Semantic-Judge Execution Contract

**Status:** Proposed  
**Spec:** V1.6 semantic-judge phase

## Context

Some evaluation obligations require semantic judgment that cannot be resolved mechanically from observable trace evidence alone. That capability must not contaminate the deterministic V1.5 core, silently change established verdict precedence, or be treated as ground truth.

V1.6 introduces a semantic-judge capability behind an explicit isolation boundary while preserving the existing deterministic evaluation kernel and its precedence rules.

## Decision

`semantic_judge` uses a structured JSON boundary, with out-of-process execution preferred for self-hosted judges:

```text
TRACE-Well core
→ JudgeRequest JSON
→ isolated judge process/service
→ JudgeResponse JSON
→ evaluator
→ PASS / FAIL / REVIEW integration
```

Open-weight, hosted, local-service, or subprocess execution are runtime choices, not distinct architecture families.

The first V1.6 milestone proves this protocol using a deterministic mock judge before any real model/provider integration.

### Verdict integration boundary

The semantic judge runs only after existing deterministic semantics have been applied.

Precedence remains:

```text
1. global specification inconsistency -> REVIEW
2. established deterministic obligation failure -> FAIL
3. unresolved required deterministic construct -> REVIEW
4. semantic judgment may be considered only if 1-3 do not already determine the outcome
```

Consequences:

- global specification inconsistency outranks deterministic behavioral judgment, including a would-be deterministic `FAIL`;
- a semantic judge cannot erase an established deterministic `FAIL`;
- semantic uncertainty or judge execution failure produces `REVIEW` rather than `PASS`;
- semantic-only final `FAIL` authority remains unresolved under ADR-0015 and is not granted by this ADR.

### Judge provenance

Judge provenance must preserve enough information to identify the judge and to determine whether exact output reproduction was expected.

The V1.6 protocol includes explicit fields for:

```text
judge_id
judge_version
execution_mode
model
model_revision
weights_digest
inference_engine
inference_engine_version
quantization
decoding_determinism_class
seed
generation_parameters
judge_prompt_version
rubric_version
```

`decoding_determinism_class` is first-class provenance and must not be inferred only from a generic generation-parameters object.

Initial values:

```text
deterministic
seeded_stochastic
unseeded_stochastic
unknown
```

This classification describes expected reproducibility behavior. It does not establish semantic correctness.

### Validation boundary

A semantic judge:

- is not ground truth;
- requires validation against blinded human/domain-expert labels before consequential use;
- cannot erase established deterministic outcomes;
- remains outside V1.5 acceptance and claims;
- must not introduce model/inference dependencies into the base deterministic runtime.

## Consequences

Heavy inference dependencies stay outside the core environment. Future judge implementations can vary while retaining a stable capability contract.

The protocol can be tested before any model integration using a deterministic mock subprocess, including timeout, malformed JSON, schema violation, non-zero exit, and disagreement paths.

Calibration, multi-judge disagreement handling, stochastic repetition analysis, and semantic-only FAIL authority remain separate later decisions.

## Alternatives rejected

- Making one model/provider part of the tracked architecture: rejected as unnecessarily specific.
- Mandatory in-process inference: rejected because it expands the core dependency/runtime boundary.
- Treating semantic judgment as authoritative ground truth: rejected.
- Letting semantic judgment override global specification inconsistency or deterministic FAIL: rejected because it would weaken existing evaluation semantics.
- Inferring judge reproducibility only from generation parameters: rejected because downstream variance analysis needs an explicit determinism class.

---

**Related ADRs:** 0004, 0015, 0016, 0019, 0020
