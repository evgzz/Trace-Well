# AGENTS.md

> Repository-level instructions for coding agents and contributors working on the `semantic-judge-v1.6` branch.

## Mission

Extend TRACE-Well with an isolated semantic-judge capability **without changing the frozen V1.5 deterministic mechanism or its claims**.

Priority order:

1. correctness;
2. reproducibility;
3. inspectable evidence;
4. isolation from the deterministic core;
5. conservative verdict semantics;
6. minimal scope;
7. public-repository neutrality.

The V1.5 evidence anchor is commit:

```text
791c92c3da43e33a2e986e63f2f7ef9f845ac70b
```

`freeze/v1.5.0-pending-po9` is a convenience branch pointing to that freeze point. Do not use V1.6 work to retroactively expand V1.5 claims.

## V1.6 product boundary

V1.6 milestone 1 adds only the semantic-judge execution protocol and conservative integration seam described in `docs/V1.6_SCOPE.md` and ADR-0017.

It is not yet:

- a validated semantic evaluator;
- a clinical judgment system;
- a model leaderboard;
- a production safety platform;
- a release-governance engine;
- a statistical reliability study;
- a multi-judge ensemble system.

Real-model integrations, human calibration, disagreement analysis, semantic-only FAIL authority, and statistical claims remain later milestones unless explicitly admitted through scope/ADR changes.

## V1.5 freeze rule

The V1.5 deterministic kernel remains the reference behavior.

Do not change V1.5 semantics merely to make semantic-judge integration easier. In particular, preserve:

- CasePair authority over cross-condition expectations;
- deterministic evaluator/comparator behavior;
- global specification inconsistency precedence;
- deterministic FAIL preservation;
- REVIEW non-promotion;
- paired mitigation verification;
- canonical artifact identity rules;
- public claims ceiling for V1.5.

Defect fixes to shared code must be clearly identified and tested against V1.5 behavior.

## Canonical documentation ownership

- `docs/V1.6_SCOPE.md` — V1.6 milestone boundary and semantic integration rules.
- `docs/adr/0017-semantic-judge-isolation.md` — semantic-judge isolation/provenance architecture.
- `docs/adr/README.md` — ADR registry/status.
- `docs/EVALUATION_SPEC.md` — established V1.5 deterministic comparator precedence.
- `docs/MVP_SCOPE.md`, `docs/PRD.md`, `docs/ACCEPTANCE.md` — V1.5 claims/proof state; do not rewrite them to make V1.6 look complete.

Do not redefine canonical V1.5 schemas in V1.6 convenience docs. Link instead.

## ADR rule

When making a load-bearing V1.6 choice not covered by an existing ADR, create a new `Proposed` ADR before implementation.

ADR-0015 remains **Proposed**. Do not grant semantic-only judgment final FAIL authority until that decision is explicitly resolved with appropriate calibration evidence.

ADR-0017 remains the controlling Proposed architecture for semantic-judge isolation during milestone 1.

Never rewrite the Decision section of an Accepted ADR. Supersede accepted history with a new ADR.

## Dependency boundary

Semantic-model or inference dependencies must not enter the base runtime.

For milestone 1, prefer:

1. Python standard library;
2. existing approved dependencies;
3. repository-owned protocol code;
4. isolated subprocess/service boundaries.

A mock semantic judge is preferred before any real provider/model dependency.

## Semantic-judge rules

- The judge is not ground truth.
- The judge consumes observable evidence only; hidden chain-of-thought is never requested or required.
- Judge request/response objects must use strict structured schemas.
- Out-of-process execution is preferred for self-hosted judges.
- Judge execution failures, malformed output, schema failures, request mismatches, and timeouts must not silently become PASS.
- Judge provenance must include an explicit `decoding_determinism_class` in addition to generation parameters.
- Real judges require validation against blinded human/domain-expert labels before consequential use.

## Verdict precedence

V1.6 milestone 1 must preserve:

```text
1. global specification inconsistency -> REVIEW
2. established deterministic obligation failure -> FAIL
3. unresolved required deterministic construct -> REVIEW
4. semantic judgment may be considered only if 1-3 do not already determine the outcome
```

Therefore:

- global specification inconsistency outranks deterministic behavioral judgment, including would-be FAIL;
- semantic judgment cannot erase an established deterministic FAIL;
- semantic uncertainty remains REVIEW;
- semantic-only candidate FAIL maps conservatively to REVIEW until ADR-0015 is resolved.

## Testing gate

Before considering a change complete, run:

```bash
pytest
python scripts/check_public_text.py
```

Tests for semantic-judge milestone 1 must include:

- valid strict response;
- explicit determinism-class provenance;
- malformed JSON;
- response schema failure;
- request-ID mismatch;
- non-zero process exit;
- timeout;
- global specification inconsistency precedence;
- deterministic FAIL preservation;
- semantic-only candidate FAIL not gaining final FAIL authority.

## Public-text gate

Do not persist private employment, recruiting, interview, application, customer-targeting, prospect-targeting, or private partnership context in tracked surfaces.

If private development material contains sensitive proper nouns, maintain an untracked `.private/sensitive_terms.txt`. Do not hardcode private names into public scanner logic.

## Claims discipline

V1.6 milestone-1 semantic judge outputs remain **prototype evaluation-engineering evidence**.

Do not claim semantic outputs establish clinical ground truth, validated expert judgment, clinical validity, patient safety, comprehensive model safety, regulatory compliance, statistical generalization, or production readiness.

## Data rules

Synthetic/public test data only for milestone 1. No PHI, live patient records, production clinical data, secrets, or credentials.

## Final engineering principle

When design choices conflict, prefer the option that keeps semantic judgment isolated, provenance explicit, deterministic semantics unchanged, uncertainty visible, and future human calibration possible.
