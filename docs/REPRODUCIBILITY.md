# TRACE-Well V1.5 — Reproducibility

> Defines what it means to reproduce a V1.5 evaluation result and how PO-9 is demonstrated. Canonical domain and manifest fields remain in `docs/ARCHITECTURE.md`.

## 1. Purpose

V1.5 supports this claim:

> **A third party can identify the exact effective evaluation artifact and explicit execution configuration, rerun the deterministic evaluation without relying on unstored author knowledge, and obtain the same evaluation conclusion.**

This is a deterministic engineering reproducibility claim, not a claim that future stochastic model executions are byte-identical.

## 2. PO-9

PO-9 requires:

```text
stable effective artifact identity
+
explicit execution configuration
+
repeatable deterministic conclusion
```

All three are necessary. A hash alone is insufficient.

## 3. Three reproducibility questions

### Artifact identity
Did two runs use the same effective evaluation specification?

Primary evidence: `artifact_digest` + `canonicalization_version`.

### Execution reproducibility
Given the same effective artifact and deterministic run configuration, does TRACE-Well produce the same evaluation conclusion?

### Independent reproduction
Can another operator reproduce the evaluation without undocumented author knowledge?

## 4. Authoring representation is not semantic identity

Formatting-only YAML/JSON changes must not alter semantic CasePair identity.

```text
source representation ≠ effective artifact identity
```

## 5. Canonical pipeline

```text
authored source
→ parse
→ domain validation
→ resolve effective object
→ canonical representation
→ artifact_digest
→ execute the exact same effective object
```

Never digest object A and execute materially different object B.

## 6. `artifact_digest` versus `source_digest`

`artifact_digest` identifies the canonical effective evaluation artifact.

`source_digest`, if present, identifies exact authored bytes.

Do not conflate them.

## 7. Canonicalization version

Persist `canonicalization_version` as defined by architecture. Any serialization-rule change capable of altering canonical output for an otherwise equivalent effective object requires a version increment.

## 8. Identity-bearing values

Follow `ARCHITECTURE.md` canonicalization rules:

- reject unconstrained binary floats in identity-bearing fields;
- preserve semantically meaningful array order;
- use deterministic optional-field treatment;
- declare evaluation-significant fixture markers identity-bearing.

## 9. Manifest completeness

The canonical RunManifest schema is owned by `ARCHITECTURE.md §20`.

Every value capable of materially changing execution/evaluation must be part of the effective artifact or explicit persisted run provenance.

Do not rely on developer memory, shell history, unstored defaults, implicit agent mode, or undocumented evaluator versions.

## 10. Explicit null versus forgotten provenance

An inapplicable value and an unknown/forgotten value are not equivalent.

Where architecture defines a provenance field that does not apply, persist explicit null rather than silently omitting it.

## 11. Execution source

Persist whether traces originated from `agent_runner` or `trace_source`.

Equivalent verdict semantics do not imply identical execution provenance.

## 12. Code identity

Persist code revision where available. If unavailable, do not invent a SHA; use the documented null/fallback behavior and preserve available package/runtime identity.

## 13. Evaluator versioning

Any evaluator change capable of altering construct derivation, observed values, or verdict semantics requires evaluator-version change.

## 14. Reference-agent mode

The canonical RunManifest includes `agent_mode`.

Examples:

```text
respect_tool_boundary
violate_tool_boundary
```

`agent_mode` is execution configuration, not agent identity, agent version, or CasePair identity.

The same `agent_id`/`agent_version` may therefore produce different traces under different recorded modes.

## 15. Deterministic reproducibility target

For the same effective CasePair, agent mode, tool policy, evaluator versions, and code/runtime configuration, rerun should reproduce the same required construct values, deterministic violations, and pair verdict.

## 16. What need not be byte-identical

Run-specific administrative values may differ, including run ID, timestamp, or local output path.

Reproducibility means equivalent deterministic evaluation semantics, not byte-for-byte equality of every generated file.

## 17. Persisted evidence

Persist enough evidence to reconstruct:

- what was evaluated;
- what traces were evaluated;
- what construct values were produced;
- what pair result was produced;
- what execution configuration applied;
- what version context applied.

Never store secrets.

## 18. Imported-trace reproducibility

For `trace_source` runs:

1. preserve the external traces used as input;
2. validate them;
3. record external execution origin;
4. reevaluate using the same deterministic evaluator/comparator.

This proves repeatable **evaluation of fixed external evidence**. It does not prove TRACE-Well can regenerate the external runtime's original traces.

## 19. Built-in versus imported reproduction

### Built-in replay

```text
CasePair + recorded deterministic execution config
→ regenerate traces
→ reevaluate
```

### Imported-trace re-evaluation

```text
persisted conforming traces + recorded evaluator config
→ reevaluate
```

These establish different reproducibility properties.

## 20. Equivalent-authoring test

Use two actually different source representations with the same semantics.

Example A:

```yaml
pair_id: example
version: 1
```

Example B:

```yaml
version: 1
pair_id: "example"
```

Assuming both resolve to the same validated effective object:

```text
same canonical representation
same artifact_digest
```

## 21. Meaningful-change test

Change one identity-bearing semantic value.

Expected:

```text
different effective object
different artifact_digest
```

## 22. Float rejection test

Introduce an unconstrained float into an identity-bearing field.

Expected: validation failure before `artifact_digest` is produced.

## 23. Canonicalization repeatability

Canonicalize the same effective object repeatedly.

Expected: same canonical representation and same `artifact_digest`.

## 24. Deterministic rerun test

Run the same CasePair with identical recorded deterministic configuration twice.

Expected: same required construct values, same deterministic failure set, same pair verdict.

## 25. Run-configuration sensitivity test

Change only `agent_mode`, for example:

```text
respect_tool_boundary → violate_tool_boundary
```

Expected:

```text
same CasePair artifact_digest
different agent_mode in manifest
different execution provenance
trace/verdict may change
```

This protects `benchmark specification ≠ execution configuration`.

## 26. Artifact change versus execution change

### Artifact change
Change the CasePair specification → `artifact_digest` changes.

### Execution change
Change only `agent_mode` → `artifact_digest` unchanged, provenance changes, trace/verdict may change.

## 27. Independent reproduction procedure

A third party should be able to:

1. obtain repository/package revision;
2. install documented base environment;
3. obtain persisted effective artifact;
4. verify artifact identity;
5. inspect `execution_source`, `agent_mode`, and other recorded configuration;
6. rerun deterministic execution;
7. rerun evaluation;
8. compare construct values;
9. compare pair verdict;
10. inspect evidence references.

No unstored author knowledge should be necessary.

## 28. Reproduction mismatch handling

If deterministic reproduction differs, inspect in order:

- artifact identity;
- canonicalization version;
- execution source;
- agent identity/version;
- agent mode;
- tool-policy version;
- evaluator versions;
- code/runtime identity.

Do not silently overwrite either result.

## 29. Reproducibility is not validity

A reproducible result may still use a poor construct or weak pair design.

Reproducibility establishes recreation under specified conditions, not clinical/scientific validity.

## 30. Reproducibility is not hashing

A matching `artifact_digest` does not by itself establish that execution or verdict was reproduced.

Artifact identity is necessary, not sufficient.

## 31. PO-9 proof matrix

| Requirement | Demonstration |
|---|---|
| Formatting-independent identity | equivalent YAML → same `artifact_digest` |
| Semantic distinction | meaningful change → different `artifact_digest` |
| Numeric identity discipline | unconstrained float → reject |
| Canonicalization stability | same effective object → same canonical form/digest |
| Explicit run config | no evaluation-critical implicit defaults |
| Artifact/run separation | `agent_mode` change preserves pair digest but changes provenance |
| Deterministic rerun | same conditions → same conclusion |
| Independent reproduction | another operator follows §27 successfully without author knowledge |

The final row is a procedural reproduction exercise, not a unit/CI assertion.

PO-9 is not Proven until all applicable rows are demonstrated.

## 32. CI checks

CI should test at minimum:

- equivalent authoring → same digest;
- semantic change → different digest;
- float rejection;
- canonicalization repeatability;
- required provenance present;
- `agent_mode` present where applicable;
- deterministic rerun → same verdict;
- agent-mode-only change leaves pair digest unchanged.

CI does **not** prove the independent-operator row; that is validated through the §27 clean-environment procedure.

No model credentials, semantic judge, or network inference are required.

## 33. Holdout

CI may validate holdout parsing, schema, canonicalization, and artifact identity. Holdout behavioral execution remains governed by `BENCHMARK_DESIGN.md`.

## 34. Future semantic-model reproducibility

Future model-backed runs may require additional model/inference provenance. Those are deferred semantic-phase concerns and are not required merely to satisfy deterministic V1.5 PO-9.

## 35. What this document does not define

This document does not redefine the RunManifest schema, CasePair schema, comparator precedence, benchmark inventory, publication scan, or semantic-judge architecture.

## 36. Definition of done

PO-9/reproducibility is ready only when canonical identity, equivalent-format tests, meaningful-change tests, numeric discipline, explicit run configuration, `agent_mode`, evaluator versions, deterministic rerun, imported-trace distinction, and the independent reproduction procedure are all demonstrated.

## 37. Final rule

> **TRACE-Well V1.5 is reproducible only when the effective benchmark artifact is canonically identifiable, every evaluation-relevant execution condition—including agent mode—is explicit, and an independent operator can rerun the deterministic evaluation to the same conclusion without relying on unstored author knowledge.**
