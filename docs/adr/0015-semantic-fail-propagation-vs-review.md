# ADR-0015 — Semantic FAIL Propagation versus REVIEW

**Status:** Proposed  
**Spec:** `docs/V1.6_EVALUATION_PLAN.md`

## Context

TRACE-Well V1.5 establishes deterministic behavioral verdicts from explicit, inspectable constructs. V1.6 introduces an isolated semantic judge for constructs that cannot be resolved mechanically from observable trace evidence alone.

The semantic judge is not ground truth. Before empirical calibration exists, a semantic candidate `FAIL` is conservatively integrated as final `REVIEW`, and semantic-only `SafetyFinding` creation is prohibited.

This ADR is intentionally written **before** the first real-model calibration study is completed. Its purpose is to pre-register the evidence and governance conditions that would be required before changing semantic FAIL authority, rather than allowing those criteria to be shaped after seeing favorable or unfavorable results.

## Current default

While this ADR remains Proposed:

```text
semantic candidate PASS   -> PASS only when the deterministic path is otherwise clear
semantic candidate FAIL   -> REVIEW
semantic candidate REVIEW -> REVIEW
semantic-only SafetyFinding -> prohibited
```

Existing deterministic precedence remains unchanged:

```text
global specification inconsistency -> REVIEW
deterministic FAIL                 -> FAIL
deterministic REVIEW               -> REVIEW
```

A semantic judge cannot erase a deterministic `FAIL` and cannot override global specification inconsistency.

## Question

Under what evidence conditions, if any, should a semantic-only candidate `FAIL` be permitted to propagate to final `FAIL` rather than `REVIEW`?

This question is separate from:

- whether the serving transport works;
- whether a model can emit valid `JudgeResponse` JSON;
- whether a judge agrees with itself;
- whether one small study happens to show high agreement;
- whether semantic-only `SafetyFinding` authority should exist.

## Pre-registered evidence stages

### Stage A — transport and prompt integrity

Before semantic quality evidence is interpretable:

```text
[ ] local transport path is validated independently of candidate-model quality
[ ] exact immutable model revision is recorded
[ ] serving-engine name/version are recorded
[ ] chat-template source is identified
[ ] chat_template_digest is recorded
[ ] rendered_prompt_digest is recorded for the effective judged request
[ ] raw request/response sanity check is completed
[ ] prompt/template fallback or mismatch is excluded or documented
```

Failure at Stage A is an integration defect, not evidence about semantic judge quality.

### Stage B — initial blinded calibration study

The initial V1.6 study uses the frozen domain-agnostic text-only corpus described in `docs/V1.6_EVALUATION_PLAN.md`.

Required evidence:

```text
[ ] 24-item corpus frozen before model outputs are inspected
[ ] human/domain-expert labels collected blind to judge output
[ ] judge outputs collected with complete provenance
[ ] each admitted configuration repeated at least 3 times
[ ] exact label agreement and PASS/FAIL/REVIEW confusion counts reported
[ ] repeat instability reported
[ ] disagreement taxonomy reviewed
[ ] prompt/template, serving, and artifact errors separated from semantic errors
```

**Stage B cannot authorize semantic-only FAIL**, regardless of the observed agreement rate.

Its only authority-relevant outcome is one of:

```text
STOP      -> evidence is insufficient or failure modes are unacceptable
REFINE    -> rubric/corpus/integration needs revision and preregistration before another study
ADVANCE   -> evidence is strong enough to justify designing a separate validation phase
```

`ADVANCE` does not mean ADR-0015 is Accepted.

### Stage C — separate validation phase

A future validation phase must be specified and frozen **before** examining its outcomes.

At minimum it must define in advance:

- target population/domain for claims;
- independent validation items not used to develop the rubric or judge prompt;
- human-reference process and adjudication policy;
- treatment of human disagreement;
- minimum repeatability requirements;
- error categories that automatically block semantic-only FAIL authority;
- any quantitative operating thresholds;
- confidence intervals or uncertainty treatment if statistical claims are proposed;
- exact model/revision/prompt/template/serving configuration under evaluation;
- whether authority is model-specific, construct-specific, domain-specific, or more general.

No numerical acceptance threshold is defined in this ADR because there is not yet empirical or domain evidence sufficient to justify one without post-hoc tuning.

Any threshold later proposed must itself be preregistered before Stage C outcomes are inspected.

## Decision options after validation evidence exists

This ADR may eventually be resolved to one of the following classes of decision.

### Option 1 — retain REVIEW-only semantic authority

```text
semantic candidate FAIL -> REVIEW
```

Use when semantic evidence is useful for triage but insufficient for autonomous failure propagation.

### Option 2 — constrained semantic FAIL authority

Permit semantic candidate `FAIL` to propagate only for explicitly validated combinations such as:

```text
construct + rubric version + model/revision + prompt/template + execution configuration + domain
```

Anything outside the validated envelope remains `REVIEW`.

### Option 3 — broader semantic FAIL authority

A broader policy would require substantially stronger evidence than the initial V1.6 study and must state exactly which dimensions may vary without revalidation.

This option is not presumed or preferred by this Proposed ADR.

## SafetyFinding authority is a separate decision

Even if semantic-only final `FAIL` is eventually accepted, semantic-only `SafetyFinding` creation does not follow automatically.

The finding lifecycle must be separately updated and tested before semantic output may create, close, or mutate a `SafetyFinding`.

Until that explicit change occurs:

```text
SafetyFinding authority = deterministic-only
```

## Evidence that does not satisfy this ADR

The following are insufficient on their own:

- a successful API/server integration;
- coherent-looking judge outputs;
- temperature set to zero;
- one model's self-consistency;
- agreement between two LLM judges without human reference labels;
- high agreement on development items used to tune the rubric;
- a small favorable calibration set without independent validation;
- aggregate accuracy that hides PASS↔FAIL errors;
- results from a prompt/template path whose effective rendering is not pinned;
- claims transferred from another model revision, quantization, domain, or serving configuration without evidence.

## Provenance requirements

Authority-relevant semantic evidence must retain, where applicable:

```text
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
chat_template_digest
rendered_prompt_digest
```

Model identity alone is not the effective judge identity.

## Consequences while Proposed

- semantic candidate `FAIL` remains `REVIEW`;
- semantic uncertainty remains `REVIEW`;
- deterministic FAIL remains authoritative;
- global specification inconsistency still outranks behavioral adjudication;
- semantic-only `SafetyFinding` creation remains prohibited;
- the initial 24-item study cannot change runtime authority;
- empirical results may motivate a separately preregistered validation phase, but cannot retroactively redefine these criteria.

## Alternatives rejected at this stage

- **Immediate semantic FAIL propagation:** rejected because no blinded validation evidence exists.
- **Use the initial 24-item study as the authority threshold:** rejected as underpowered for authority and vulnerable to post-hoc threshold selection.
- **Treat judge self-consistency as validation:** rejected because repeatability is not correctness.
- **Treat human labels as infallible ground truth:** rejected; human disagreement and adjudication uncertainty must remain visible.
- **Allow semantic FAIL to create SafetyFindings automatically:** rejected because verdict authority and finding-lifecycle authority are separate decisions.

---

**Related ADRs:** 0002, 0004, 0010, 0016, 0017, 0019, 0020
