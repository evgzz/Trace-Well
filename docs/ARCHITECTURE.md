# TRACE-Well V1.5 — Architecture

> Canonical source for V1.5 domain objects, interfaces, capability seams, artifact identity, and run provenance.

## 1. Purpose

TRACE-Well V1.5 is a small paired/counterfactual behavioral **evaluation harness**.

The architecture is a compact **evaluation kernel** around a stable boundary:

```text
CasePair
→ execution through agent_runner or trace_source
→ observable Trace × 2
→ construct-level evaluation
→ shared BehaviorDeltaComparator
→ PASS / FAIL / REVIEW
→ finding / paired verification
→ persisted evidence
```

Execution runtimes may vary; **evaluation semantics do not**.

## 2. Layer model

1. **Authoring** — `case_loader`
2. **Resolution / identity** — effective object + canonicalization
3. **Execution** — `agent_runner` or `trace_source`
4. **Evaluation** — deterministic construct evaluation
5. **Comparison** — one BehaviorDeltaComparator
6. **Finding / verification** — regression evidence and paired rerun
7. **Evidence** — traces, results, manifests, findings

## 3. Capabilities

V1.5 uses capability vocabulary rather than provider-specific adapters:

- `case_loader`
- `agent_runner`
- `trace_source`
- `semantic_judge` — future / deferred

Provider/model/runtime identity belongs in run provenance, not the architecture taxonomy.

## 4. Case

Canonical logical fields:

```text
case_id
version
scenario_family
messages
context
tool_policy
evaluation_contract
metadata
```

`messages` is an ordered fixed script for V1.5 multi-turn cases.

Free-form `metadata` is non-semantic and excluded from `artifact_digest` unless a value is explicitly modeled as identity-bearing. Contradiction markers or trajectory state markers must therefore be explicit structured fixture fields or explicitly identity-bearing metadata by schema rule; evaluation-significant state must never be smuggled through arbitrary metadata.

## 5. CasePair

```text
pair_id
version
canonical_case
perturbed_case
controlled_variable
expected_changes: list[ExpectedChange]
expected_invariants: list[ExpectedInvariant]
tags
```

`CasePair.expected_changes` and `CasePair.expected_invariants` are the authoritative source for cross-condition expectations.

Reference-agent mode is **not** CasePair identity.

## 6. EvaluationContract

Within-condition obligations only:

```text
required_behaviors
prohibited_behaviors
required_escalation
allowed_tools
prohibited_tools
required_evidence
```

An EvaluationContract does not own cross-condition deltas.

If a condition contract conflicts materially with the CasePair expectation, the comparator emits deterministic global `REVIEW` with machine-readable evidence. TRACE-Well does not auto-repair authored inconsistency.

## 7. ExpectedChange

```text
construct
from
to
```

`from` and `to` support JSON-scalar values sufficient for V1.5 transitions:

- boolean;
- string categorical values;
- integer;
- exact normalized numeric representation where permitted;
- null.

Unconstrained identity-bearing binary floats are rejected.

## 8. ExpectedInvariant

```text
construct
rule
value
evidence_refs
```

V1.5 rules:

- `unchanged` — `value` optional; canonical and perturbed observed values must match;
- `equals` — `value` required; both conditions must equal the required value.

V1.5 does not permit arbitrary executable predicates in benchmark artifacts.

## 9. Trace

```text
trace_id
run_id
case_id
events: list[TraceEvent]
```

A Trace contains observable events only. Hidden chain-of-thought is never captured.

## 10. TraceEvent

```text
event_id
timestamp
event_type
actor
input
output
tool
tool_arguments
tool_result
authorization_state
evidence_refs
metadata
```

Supported event types include:

- `user_message`
- `context_retrieval`
- `agent_response`
- `tool_call`
- `tool_result`
- `escalation`

A `TraceEvent(event_type="escalation")` is evidence. The evaluator derives the construct `escalation`; event type and construct are not the same schema concept.

## 11. EvaluationResult

```text
result_id
case_id
evaluator_id
label
construct
observed_value
rationale
evidence_refs
metadata
```

Labels are:

```text
PASS
FAIL
REVIEW
```

`rationale` is explanatory text, not privileged reasoning evidence.

## 12. ConditionEvaluation

```text
list[EvaluationResult]
```

One result per evaluated construct. Do not aggregate a condition to one verdict before pair comparison.

## 13. ObservedChange

```text
construct
canonical_value
perturbed_value
changed
evidence_refs
```

The persisted canonical name is `observed_changes`; do not introduce `observed_delta` as a competing field.

## 14. BehaviorDeltaResult

```text
pair_id
canonical_results
perturbed_results
expected_changes
observed_changes
expected_invariants
invariant_violations
pair_result
evidence_refs
metadata
```

Pair result is `PASS`, `FAIL`, or `REVIEW` according to `docs/EVALUATION_SPEC.md`.

## 15. SafetyFinding

```text
finding_id
pair_id
case_family
failure_type
expected_changes
observed_changes
invariant_violations
evidence_refs
proposed_mitigation
closure_criteria
verification_run
status
```

Statuses:

```text
OPEN
MITIGATED
VERIFYING
CLOSED
REVIEW
```

Normal behavioral-regression findings are created for pair `FAIL`, not for specification inconsistency `REVIEW`.

## 16. Agent interface

Built-in execution presents a provider-independent interface conceptually equivalent to:

```text
Agent.run(case) -> Trace
```

For fixed multi-turn cases, `run(case)` processes the complete ordered `Case.messages` script and produces one final Trace containing all observable events.

No adaptive simulator is part of V1.5.

## 17. Deterministic reference agent

Required modes:

- `respect_context`
- `ignore_context`
- `detect_contradiction`
- `ignore_contradiction`
- `respect_tool_boundary`
- `violate_tool_boundary`
- `respect_late_context`
- `ignore_late_context`
- `always_escalate`

These modes are run configuration, not CasePair identity.

## 18. Mock tools

V1.5 supports deterministic mock tools sufficient for the mechanism proof, including:

```text
retrieve_history()
request_human_review()
execute_action()
```

Tool calls and authorization state must be observable in traces.

## 19. External trace source

Conforming external traces are a first-class execution source.

A CLI path may conceptually expose:

```text
tracewell evaluate-traces canonical.json perturbed.json pair.json
```

External traces must pass strict conformance. Missing events are never guessed or synthesized to make an evaluation scoreable.

Built-in and imported traces then enter the **same evaluator and same comparator**.

## 20. RunManifest

Canonical run provenance fields:

```text
run_id
timestamp

case_pair_id
case_pair_version
artifact_digest
canonicalization_version

execution_source

agent_id
agent_version
agent_mode

model
model_version
prompt_version

tool_policy_version
evaluator_versions

code_sha
runtime_version
```

`execution_source` distinguishes at minimum `agent_runner` from `trace_source`.

`agent_mode` records the deterministic reference-agent behavior configuration for the run, such as `respect_tool_boundary` or `violate_tool_boundary`. It is execution configuration, not agent identity, agent version, or CasePair identity. Where the concept does not apply, persist explicit null.

For the deterministic reference agent, model-related fields are explicit null where inapplicable.

`code_sha` may be null when execution is outside a Git checkout; do not invent a revision.

Every configuration value capable of materially changing execution/evaluation must be part of the effective artifact or explicit persisted provenance.

## 21. Canonical artifact identity

The identity pipeline is:

```text
authored YAML/JSON
→ parse
→ Pydantic/domain validation
→ resolve effective object
→ canonical JSON
→ SHA-256 artifact_digest
→ execute the exact same effective object
```

`source_digest` is optional for exact authored-byte identity and is distinct from `artifact_digest`.

## 22. Canonicalization rules

- Persist `canonicalization_version`.
- Preserve semantically meaningful array order.
- Exclude non-semantic free-form metadata from artifact identity.
- Evaluation-significant values must live in explicit identity-bearing fields.
- Any serialization-rule change capable of altering canonical output requires a new canonicalization version.

## 23. Numeric identity rule

Unconstrained binary floating-point values are rejected in identity-bearing fields.

If fractional identity values are required, use an exact normalized representation such as a decimal string under an explicit schema rule.

## 24. One evaluation path

There is one deterministic evaluation/comparison semantic path:

```text
Trace × 2
→ construct evaluation
→ ConditionEvaluation × 2
→ specification consistency
→ observed changes + invariant checks
→ BehaviorDeltaComparator
→ pair_result
```

Do not create separate comparator logic for imported traces, CLI commands, benchmark families, or mitigation verification.

## 25. Specification consistency boundary

`CasePair` owns cross-condition expectation.

`EvaluationContract` owns within-condition obligations.

Material inconsistency is deterministic global `REVIEW` and is not silently repaired.

## 26. Evaluator ownership

The exact comparison algorithm and verdict precedence are owned by `docs/EVALUATION_SPEC.md`, not this document.

## 27. Paired verification

A mitigation verification run reuses the same CasePair, contracts, evaluators, expected changes/invariants, comparator, and verdict rules, and reruns **both** conditions.

A one-sided rerun cannot close the finding.

## 28. Persistence

V1.5 uses inspectable file-based evidence rather than requiring a database.

Persist enough evidence to inspect:

- effective artifact identity;
- traces;
- construct evaluations;
- pair comparison;
- finding/verification state where applicable;
- run manifest.

Never persist secrets.

## 29. Dependencies

Base runtime dependency ceiling is enforced by `tests/test_dependency_boundary.py` and ADR-0016.

Heavy semantic/inference dependencies are not mandatory base dependencies.

## 30. Semantic evaluation

Semantic judgment is deferred beyond deterministic V1.5 acceptance.

If later implemented, it uses the `semantic_judge` capability boundary, remains non-ground-truth, and cannot erase established deterministic failure.

## 31. No hidden chain-of-thought

TRACE-Well never requests, captures, persists, requires, or evaluates hidden chain-of-thought.

Observable rationale may be stored as ordinary output but is not privileged provenance.

## 32. Cross-document ownership

| Concern | Canonical owner |
|---|---|
| Scope/non-goals/claims | `MVP_SCOPE.md` |
| Proof obligations | `PRD.md` |
| Decision rationale | `docs/adr/` |
| Schemas/interfaces/provenance | `ARCHITECTURE.md` |
| Verdict algorithm | `EVALUATION_SPEC.md` |
| Fixture design | `BENCHMARK_DESIGN.md` |
| Reproduction procedure | `REPRODUCIBILITY.md` |
| Evidence interpretation limits | `LIMITATIONS.md` |

## 33. Architecture definition of done

- all canonical objects have one owning definition;
- `CasePair` is cross-condition source of truth;
- built-in/imported traces converge on one evaluator/comparator;
- `agent_mode` is explicit run provenance;
- canonical artifact identity is deterministic;
- paired verification reruns both conditions;
- deterministic core remains credential-free;
- no hidden chain-of-thought is required.

## 34. Architectural invariants

**A1 — CasePair source of truth:** cross-condition expectations live in CasePair.  
**A2 — One comparator:** all supported execution sources use one BehaviorDeltaComparator semantic path.  
**A3 — Construct-level evaluation:** conditions remain construct-keyed until comparison.  
**A4 — REVIEW explicit:** unresolved/spec-inconsistent evaluation is never silently converted to PASS.  
**A5 — Observable evidence only:** no hidden chain-of-thought dependency.  
**A6 — Canonical artifact identity:** effective semantics, not source formatting, define `artifact_digest`.  
**A7 — Paired verification:** mitigation reruns both conditions.  
**A8 — Deterministic core:** base acceptance is credential-free and reproducible.

These invariants constrain implementation; they are not additional product features.

## 35. Final architecture statement

> **TRACE-Well V1.5 is architected as a small evaluation kernel around a stable paired-evidence boundary. Execution runtimes may vary, but evaluation semantics, artifact identity rules, and verdict discipline do not.**
