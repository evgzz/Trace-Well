# ADR-0021 — Judge Provenance Binding

**Status:** Proposed  
**Spec:** `docs/V1.6_SCOPE.md`; extends ADR-0017

## Context

ADR-0017 defines which provenance fields a `JudgeResponse` carries. It does not define who computes the content digests, or whether the caller verifies that the returned provenance identifies the judge it configured. Under the original adapters:

- `chat_template_digest` and `rendered_prompt_digest` were free-form CLI strings, asserted by the operator rather than derived from content;
- nothing recorded a digest of the payload the adapter actually sent;
- any schema-valid provenance was accepted, so a misconfigured or substituted judge could be integrated as the intended one;
- adapters followed HTTP redirects, and `urllib` forwards the `Authorization` header to the redirect target.

## Decision

### Digests are computed from bytes, never asserted

| Field | Source | Computed by |
|---|---|---|
| `request_payload_digest` | exact HTTP request body sent | adapter, always |
| `chat_template_digest` | `--chat-template-file` | adapter, when the file is supplied |
| `rendered_prompt_digest` | `--rendered-prompt-file` | adapter, when the file is supplied |

Declared-file digests are computed before the inference request is sent, so a file changed during a long request cannot be recorded as the artifact that was used. All use the form `sha256:<hex>`, matching `scripts/record_model_run.py`. The asserted-string flags `--chat-template-digest` and `--rendered-prompt-digest` are removed.

`request_payload_digest` is deliberately distinct from `rendered_prompt_digest`. The adapter sends chat messages; the server applies the chat template. Per `docs/V1.6_EVALUATION_PLAN.md`, `rendered_prompt_digest` identifies the server-rendered prompt, which the adapter cannot observe. Labelling the sent payload as the rendered prompt would be incorrect provenance. When the rendered prompt or template is unavailable, the field is null, not guessed.

### Expected judge identity is verified

> Superseded in part by Amendment 1 below: `decoding_determinism_class` and `chat_template_digest` moved to `ExpectedJudgeConfiguration`, `weights_digest` was added to identity, and configuration is checked alongside identity.

A caller may supply `ExpectedJudgeIdentity` (`judge_id`, `judge_version`, `model`, `model_revision`, `decoding_determinism_class`, `judge_prompt_version`, `rubric_version`, `chat_template_digest`). Every non-null field must equal the returned provenance. Any mismatch raises `SemanticJudgeProvenanceMismatch` (a `SemanticJudgeProtocolError`, reason `JUDGE_IDENTITY_MISMATCH`) and integrates as `REVIEW`.

Expected identity is run configuration, not fixture content, so it is passed to `run_semantic_fixture` rather than stored in semantic fixtures. Omitting it preserves current behavior.

The supplied expected identity and the outcome of the comparison (`NOT_REQUESTED`, `MATCH`, `MISMATCH`, `NOT_EVALUATED`) are persisted with every semantic result, so the evidence shows whether binding was enforced and not only what the judge reported. A mismatching response is preserved as `rejected_judge_response` with `{field: {expected, observed}}` details.

### Determinism class is typed everywhere

`JudgeCalibrationRecord.decoding_determinism_class` uses the `DecodingDeterminismClass` enum, so calibration records cannot carry values the protocol does not define.

### Transport

Adapters refuse all HTTP redirects. The request body and any credential reach only the endpoint that was explicitly configured and validated.

The default subprocess budget (`DEFAULT_JUDGE_TIMEOUT_SECONDS`) must exceed the bundled adapters' HTTP timeouts, so the caller does not kill a slow but healthy judge.

## Amendment 1 — Expected judge configuration

**Status:** Accepted and implemented. This amendment supersedes the field list in "Expected judge identity is verified" above. ADR-0021 as a whole remains Proposed.

### Problem

`ExpectedJudgeIdentity` binds what judge artifact ran, but not how it ran. `JudgeProvenance` already reports execution mode, inference engine and version, quantization, seed and generation parameters, and ADR-0017 treats these as provenance that characterizes the judge and its reproducibility. Two executions can therefore satisfy the same expected identity while differing materially:

```text
model M, revision R, quantization fp16, temperature 0.0, engine vLLM-A
model M, revision R, quantization int4, temperature 0.8, engine vLLM-B
```

### Decision

Split the caller's expectation into two models over disjoint `JudgeProvenance` fields:

```text
ExpectedJudgeIdentity            what judge artifact ran
├── judge_id
├── judge_version
├── model
├── model_revision
├── weights_digest
├── judge_prompt_version
└── rubric_version

ExpectedJudgeConfiguration       how the judge ran
├── execution_mode
├── inference_engine
├── inference_engine_version
├── quantization
├── decoding_determinism_class
├── seed
├── generation_parameters
└── chat_template_digest
```

`decoding_determinism_class` and `chat_template_digest` move from identity to configuration: they describe how the judge ran, not which artifact it is. `weights_digest` is added to identity.

#### Comparison semantics

| Expected field | Rule |
|---|---|
| `null` (top-level expectation field) | unconstrained; never compared |
| scalar (`str`, `int`) | exact equality with the returned value |
| enum (`decoding_determinism_class`) | exact enum equality |
| `generation_parameters` | subset: every expected key must be present in the returned parameters with an equal value; returned keys not in the expectation are unconstrained |

Examples:

```text
expected generation_parameters {temperature: 0.0}
returned {temperature: 0.0, max_tokens: 256, top_p: 1.0}   -> MATCH
returned {temperature: 0.7, max_tokens: 256}               -> MISMATCH -> REVIEW
returned {max_tokens: 256}                                 -> MISMATCH -> REVIEW (expected key absent)

expected quantization fp16, returned int4                  -> MISMATCH -> REVIEW
```

#### Value equality

All comparisons, including each value inside `generation_parameters`, use typed equality over the normalized JSON value, never over stringified values and never Python's native `==` (under which `True == 1`):

| JSON type | Equal when |
|---|---|
| number | both are numbers (not booleans) with the same numeric value, so `0 == 0.0` |
| string | both are strings with identical content |
| boolean | both are booleans with the same value |
| null | both are null |
| array | same length and pairwise equal in order |
| object | same key set and every value pairwise equal |

Values of different JSON types are never equal:

```text
0.0        != "0.0"
1          != true
["a", "b"] != ["b", "a"]
```

The subset rule applies only at the top level of `generation_parameters`; nested objects and arrays inside a parameter value compare by the full typed equality above.

#### Two meanings of `null`

`null` means "unconstrained" **only** as the value of a top-level expectation field (for example `quantization: null` or `generation_parameters: null`). Inside `generation_parameters`, a key whose expected value is `null` constrains that key to the literal JSON `null`; the "don't care" meaning is never applied recursively:

```text
expected generation_parameters {"foo": null}
returned {"foo": null}   -> MATCH
returned {"foo": 0}      -> MISMATCH
returned {}              -> MISMATCH   (expected key absent)
```

To leave a generation parameter unconstrained, omit its key from the expectation.

#### Valid comparison inputs

Only standard JSON values are valid comparison inputs. Numbers must be finite. `NaN`, `Infinity` and `-Infinity` are invalid protocol values, not values to compare, so there is no rule for whether `NaN` equals `NaN`:

- **Expected side:** an `ExpectedJudgeIdentity` or `ExpectedJudgeConfiguration` containing a non-finite number fails validation when it is constructed and never reaches a comparison.
- **Returned side:** judge output is parsed as strict JSON. A non-finite number anywhere in the response (Python's `json.loads` accepts these tokens by default) rejects the response as `JUDGE_MALFORMED_JSON` before schema validation, so no comparison runs and both check statuses are `NOT_EVALUATED` when an expectation was supplied.

#### Evaluation and recording

- Both comparisons run on any response that passes schema, request-ID and evidence-reference validation, so both outcomes are always known together.
- Each is recorded independently with the same four-state status: `judge_identity_check` and a new `judge_configuration_check`, each one of `NOT_REQUESTED | MATCH | MISMATCH | NOT_EVALUATED`. `expected_judge_configuration` is persisted alongside `expected_judge_identity`.
- Any mismatch rejects the response under the existing rejection contract (`rejected_judge_response` preserved, `integrated_verdict = REVIEW`).
- A new reason code `JUDGE_CONFIGURATION_MISMATCH` is added.

The persisted fields have distinct, non-overlapping roles:

```text
judge_error_reason         primary rejection classification (one code)
judge_identity_check       independent identity comparison result
judge_configuration_check  independent configuration comparison result
judge_error_details        complete mismatch evidence from both checks
```

When both comparisons mismatch, `judge_error_reason` is `JUDGE_IDENTITY_MISMATCH` and both statuses record `MISMATCH`. **The reason code is only the primary classification; it is not a claim that the other check passed.** Consumers must read `judge_identity_check` and `judge_configuration_check` to learn which comparisons failed, never infer it from `judge_error_reason` alone.

Because the two models cover disjoint fields, `judge_error_details` stays a flat `{field: {expected, observed}}` map containing every mismatched field from both comparisons, with no change to the existing details shape.

### Known limitation: seed

A `null` expectation means "unconstrained", so `seed: null` cannot express "must be unseeded". No sentinel is introduced: there is no current need to distinguish "don't care about the seed" from "must be unseeded", and unseeded execution is already expressible through `decoding_determinism_class = unseeded_stochastic`. Revisit only if a qualification protocol requires the distinction.

### Migration

Moving two fields out of `ExpectedJudgeIdentity` is a breaking schema change for callers and for any persisted `expected_judge_identity` records that set them. V1.6 semantic outputs are prototype evidence and no live calibration records exist yet, so the change is made directly rather than with a compatibility shim. Implementation must land with tests covering every row of both comparison tables, the three cross-type inequalities above, the three `{"x": null}` cases above, rejection of `NaN`/`Infinity`/`-Infinity` on both the expected side (validation error) and the returned side (`JUDGE_MALFORMED_JSON`, never `MATCH` or `MISMATCH`), both precedence cases (including that a dual mismatch records `MISMATCH` in both statuses and both field sets in details), and the subset rule's absent-key case.

### Alternatives considered

- **Extend `ExpectedJudgeIdentity` with every field.** Rejected: it conflates artifact identity with execution configuration, and qualification may legitimately pin one without the other.
- **Exact equality for `generation_parameters`.** Rejected: callers would have to restate every server default (`top_p`, `max_tokens`, …) to pin a single parameter.
- **A sentinel for "must be unseeded".** Deferred; see the seed limitation above.

## Consequences

- Provenance answers "what judge ran, on what bytes?" from computed evidence, not operator assertion.
- Identity substitution or misconfiguration becomes visible `REVIEW` instead of silently attributed output.
- Runbook invocations must pass files instead of digest strings.
- Verifying that the endpoint actually *served* the supplied template remains an operator responsibility; the digest proves which file was declared, not which file the server loaded.

## Alternatives rejected

- Computing `rendered_prompt_digest` from the sent payload: rejected as mislabelled provenance.
- Keeping asserted digest strings alongside files: rejected because a string cannot be tied to content.
- Storing expected identity in semantic fixtures: rejected because fixtures describe the evaluation, not the judge deployment.

---

**Related ADRs:** 0015, 0017, 0020
