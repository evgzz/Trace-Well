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

A caller may supply `ExpectedJudgeIdentity` (`judge_id`, `judge_version`, `model`, `model_revision`, `decoding_determinism_class`, `judge_prompt_version`, `rubric_version`, `chat_template_digest`). Every non-null field must equal the returned provenance. Any mismatch raises `SemanticJudgeProvenanceMismatch` (a `SemanticJudgeProtocolError`, reason `JUDGE_IDENTITY_MISMATCH`) and integrates as `REVIEW`.

Expected identity is run configuration, not fixture content, so it is passed to `run_semantic_fixture` rather than stored in semantic fixtures. Omitting it preserves current behavior.

The supplied expected identity and the outcome of the comparison (`NOT_REQUESTED`, `MATCH`, `MISMATCH`, `NOT_EVALUATED`) are persisted with every semantic result, so the evidence shows whether binding was enforced and not only what the judge reported. A mismatching response is preserved as `rejected_judge_response` with `{field: {expected, observed}}` details.

### Determinism class is typed everywhere

`JudgeCalibrationRecord.decoding_determinism_class` uses the `DecodingDeterminismClass` enum, so calibration records cannot carry values the protocol does not define.

### Transport

Adapters refuse all HTTP redirects. The request body and any credential reach only the endpoint that was explicitly configured and validated.

The default subprocess budget (`DEFAULT_JUDGE_TIMEOUT_SECONDS`) must exceed the bundled adapters' HTTP timeouts, so the caller does not kill a slow but healthy judge.

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
