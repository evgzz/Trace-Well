# TRACE-Well

TRACE-Well V1.5 is a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Its deterministic MVP tests whether an agent makes a required behavioral change, preserves required invariants, and whether a configured mitigation survives both sides of the counterfactual using explicit, inspectable evidence.

> **Branch notice:** this README is on `semantic-judge-v1.6`. The frozen V1.5 evidence anchor is commit `791c92c3da43e33a2e986e63f2f7ef9f845ac70b`; `freeze/v1.5.0-pending-po9` remains the V1.5 freeze point. V1.6 work must not be used to retroactively expand V1.5 claims.

## V1.5 release status

| Gate | Status |
|---|---|
| Engineering / repository **Done** | ✅ Complete |
| Automated PO-1–PO-11 evidence | ✅ Complete |
| PO-9 clean-runner reproduction on a fresh CI runner | ✅ Complete |
| PO-9 blind independent-human reproduction from public documentation alone | ⬜ Pending |
| V1.5 **Fully Proven** | ⬜ Blocked only by the independent-human PO-9 signoff and operator self-attestation |

### What remains before V1.5 can be described as fully Proven

One **eligible, previously unexposed human operator** must execute [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) against the frozen V1.5 snapshot using only the public repository and ordinary public documentation for standard tools.

The operator must:

- have no prior exposure to TRACE-Well design discussions, private planning, unpublished guidance, implementation/review work, or preparation of the reproduction procedure;
- receive no TRACE-Well-specific clarification, walkthrough, or side-channel help from the author or another informed project participant during the attempt;
- reproduce the required PASS, FAIL, REVIEW, digest-invariance, development-suite, and holdout results;
- personally provide or affirmatively adopt the required first-person eligibility/no-side-channel self-attestation.

If the operator needs TRACE-Well-specific clarification, the attempt stops and the blocker is treated as a **documentation/repository-sufficiency defect**. The public material must be corrected and the reproduction re-attempted from a clean checkout; the operator must not be privately unblocked and allowed to continue the same signoff attempt.

See [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) for the authoritative V1.5 Proven/Done gate and [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) for the operator protocol.

> **Do not describe V1.5 as fully Proven until that independent-human signoff and operator self-attestation have actually been recorded.**

## V1.6 semantic-judge development status

V1.6 is an additive semantic-evaluation extension built on top of the frozen V1.5 deterministic kernel. Its current scope is defined in [`docs/V1.6_SCOPE.md`](docs/V1.6_SCOPE.md), its implementation-vs-empirical status is defined in [`docs/V1.6_ACCEPTANCE.md`](docs/V1.6_ACCEPTANCE.md), and the first empirical study is frozen in [`docs/V1.6_EVALUATION_PLAN.md`](docs/V1.6_EVALUATION_PLAN.md).

Implemented:

- strict `JudgeRequest` / `JudgeResponse` JSON protocol;
- isolated subprocess semantic-judge execution;
- deterministic mock semantic judge with protocol-failure tests;
- explicit judge provenance, including first-class `decoding_determinism_class`, `chat_template_digest`, and `rendered_prompt_digest`;
- verdict integration that preserves V1.5 precedence;
- end-to-end semantic fixtures that persist `semantic_result.json` separately from deterministic evidence;
- explicit deterministic-only `SafetyFinding` authority;
- a localhost-only OpenAI-compatible adapter for self-hosted/local model servers;
- a dedicated Hugging Face Inference Endpoints adapter for no-self-host Tier-0 testing;
- a blinded calibration harness that joins judge records to independent human labels by opaque item ID and records agreement/disagreement evidence;
- a standalone Proposed [`ADR-0015`](docs/adr/0015-semantic-fail-propagation-vs-review.md) that preregisters the evidence path for any future semantic-only FAIL decision;
- a real-model execution runbook, strict experiment-manifest schema, and provenance recorder for the first empirical model run.

`docs/V1.6_ACCEPTANCE.md` marks the implementation gate complete while keeping real-model empirical validation explicitly pending.

### Frozen initial study roles

The initial V1.6 empirical study is **domain-agnostic and text-only**:

- `Qwen/Qwen2.5-0.5B-Instruct` — Tier-0 transport control;
- `nvidia/Nemotron-Mini-4B-Instruct` — Tier-1 semantic-judge candidate, admitted only after its model-specific chat template is verified in the chosen serving stack;
- `google/medgemma-1.5-4b-it` — deferred to a later healthcare-domain specialization extension rather than included in the initial 24-item general corpus.

The frozen plan requires the exact immutable upstream model revision actually used to be recorded for every empirical run. A model name alone is not sufficient provenance.

### Tier-0 deployment options

Tier 0 has two supported paths:

- **HF Inference Endpoint** — preferred no-self-host path. Hugging Face manages the dedicated deployment while TRACE-Well calls the endpoint through `scripts/hf_endpoint_judge.py`.
- **Local/self-hosted OpenAI-compatible server** — preferred when full prompt/runtime/artifact provenance is required; TRACE-Well calls it through `scripts/local_openai_compatible_judge.py`.

Hosted dedicated-endpoint runs are `transport_only` by default. They become calibration candidates only if the deployment exposes enough exact model/template/runtime evidence to satisfy the frozen manifest and admission gates.

Unavailable hosted provenance must remain unavailable. TRACE-Well must not substitute locally inferred template/rendered-prompt values and describe them as server-observed execution evidence.

### Serving-engine policy

The initial study adds serving paths only to answer a specific provenance or reproducibility question.

Current preference:

- **HF Inference Endpoints** — preferred no-ops Tier-0 transport path for the exact Hub model when deployable;
- **vLLM** — primary local Tier-0/1 safetensors-side serving path when the selected model is admitted successfully;
- **llama.cpp** — independent GGUF cross-check when a specific artifact/quantization question warrants it, with exact repo/file, quantization, and file digest recorded;
- **Ollama** — exploratory only for calibration purposes unless the exact served Ollama blob/manifest can be reconciled to the upstream Hugging Face artifact;
- Transformers Serve, TGI, and SGLang remain valid alternate local serving options but are not required in the initial study.

Cross-engine disagreement is treated first as a possible serving/template/artifact difference, not immediately as semantic-model instability.

### Current V1.6 evidence boundary

The local OpenAI-compatible adapter is tested in CI against a fake loopback server. The dedicated Hugging Face endpoint adapter is tested in CI against a fake endpoint contract. These prove adapter/request/response behavior; they do **not** establish real-model performance or calibration.

The calibration harness exists, but no real-model calibration claim exists until actual judge outputs are compared against blinded human/domain-expert labels.

Current semantic authority remains deliberately conservative:

```text
global specification inconsistency -> REVIEW
deterministic FAIL                -> FAIL
deterministic REVIEW              -> REVIEW
semantic candidate PASS           -> PASS only when deterministic path is otherwise clear
semantic candidate FAIL           -> REVIEW
semantic candidate REVIEW         -> REVIEW
```

ADR-0015 remains **Proposed**. Its preregistered rule is stricter than a simple “run the 24-item study and decide”: the initial study cannot itself authorize semantic-only FAIL. Its authority-relevant outcome is only `STOP`, `REFINE`, or `ADVANCE` to a separately preregistered validation phase.

Semantic-only output cannot create, close, or mutate a `SafetyFinding`. The calibration harness explicitly records:

```text
semantic_fail_authority_granted: false
statistical_validity_claimed: false
```

## Current scope and claims boundary

V1.5 is a mechanism proof on controlled synthetic cases. It is not a model leaderboard, production safety platform, clinical decision-support system, release-governance engine, or statistical evaluation study.

The V1.5 public claim ceiling is **prototype engineering evaluation evidence**. TRACE-Well V1.5 does not establish clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

V1.6 semantic-judge outputs remain **prototype evaluation-engineering evidence** until real-model calibration evidence exists. They must not be described as clinical ground truth, validated expert judgment, comprehensive safety evidence, statistically validated performance, or release authorization.

## Install

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

Requires Python 3.11 or newer.

The development package and CLI version are `1.6.0.dev0`. This marks integrated V1.6 implementation work; it is not a stable `1.6.0` release and does not imply empirical validation.

## Implemented deterministic CLI commands

```bash
tracewell version
tracewell run-pair cases/dev/auth-001.yaml --mode respect_tool_boundary --run-id example-pass
tracewell evaluate-traces canonical_trace.json perturbed_trace.json cases/dev/auth-001.yaml --run-id imported-example
tracewell run-suite --cases-root cases --run-prefix suite
tracewell run-holdout --cases-root cases --run-prefix holdout
```

No semantic-judge CLI command is currently claimed as part of the public command surface. V1.6 semantic execution is currently exposed through repository modules/scripts and tests.

See [`docs/DEMO.md`](docs/DEMO.md) for the deterministic V1.5 walkthrough.

## Benchmark corpus

The frozen V1.5 corpus contains:

- 9 distinct development CasePairs;
- 18 deterministic development executions;
- 9 expected PASS directions;
- 9 expected seeded FAIL directions;
- 1 separately executed holdout CasePair;
- 1 dedicated inconsistent-specification fixture for PO-7 `REVIEW`.

Agent modes are execution configuration; they do not create additional CasePair identities.

V1.6 adds semantic fixtures separately from the frozen V1.5 benchmark inventory. Those fixtures do not change the V1.5 CasePair counts or PO-9 reproduction evidence.

## Evidence and reproducibility

Built-in and imported-trace V1.5 runs persist inspectable evidence bundles containing:

```text
manifest.json
canonical_trace.json
perturbed_trace.json
result.json
```

A deterministic `FAIL` additionally persists `finding.json`. A global `REVIEW` does not create a normal SafetyFinding.

V1.6 semantic fixture execution adds a separate:

```text
semantic_result.json
```

Authority-relevant real-model semantic provenance includes the model/revision, serving-engine identity, generation configuration, and both effective prompt digests.

For the first real-model run, [`docs/V1.6_REAL_MODEL_RUNBOOK.md`](docs/V1.6_REAL_MODEL_RUNBOOK.md) defines both hosted and local Tier-0 procedures. `experiments/v1.6/manifest.schema.json` defines the calibration-grade evidence manifest, and `scripts/record_model_run.py` hashes the exact chat template, rendered prompt, request, and response files when those artifacts genuinely correspond to the execution under study.

Semantic output does not create a semantic-only `finding.json` while ADR-0015 remains unresolved.

PO-9 automated clean-runner reproduction is implemented by:

```bash
python scripts/reproduce_po9.py
```

It writes:

```text
results/reproduction/po9-reproduction-report.json
```

The CI artifact report explicitly records that it is an automated clean runner and **not** an independent-human signoff.

## Semantic-judge implementation surfaces

Current V1.6 implementation surfaces include:

```text
tracewell/semantic_judge.py
tracewell/semantic_pipeline.py
tracewell/semantic_calibration.py
scripts/mock_semantic_judge.py
scripts/local_openai_compatible_judge.py
scripts/hf_endpoint_judge.py
scripts/record_model_run.py
experiments/v1.6/manifest.schema.json
```

The local adapter remains loopback-only. The dedicated HF endpoint adapter accepts an HTTPS managed endpoint and requires the canonical model id plus immutable model revision to be supplied explicitly.

## Canonical specification

For the frozen V1.5 base, read:

1. [`docs/MVP_SCOPE.md`](docs/MVP_SCOPE.md) — scope, non-goals, claims ceiling, Proven vs Done.
2. [`docs/PRD.md`](docs/PRD.md) — PO-1 through PO-11.
3. [`docs/PO_ADR_MAP.md`](docs/PO_ADR_MAP.md) — proof-to-decision traceability.
4. [`docs/adr/README.md`](docs/adr/README.md) — authoritative ADR registry.
5. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — canonical schemas, capabilities, artifact identity, run provenance.
6. [`docs/EVALUATION_SPEC.md`](docs/EVALUATION_SPEC.md) — deterministic comparator and verdict precedence.
7. [`docs/BENCHMARK_DESIGN.md`](docs/BENCHMARK_DESIGN.md) — distinct CasePair design, controls, holdout, Proven coverage.
8. [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) — PO-9 end-to-end semantics.
9. [`docs/LIMITATIONS.md`](docs/LIMITATIONS.md) — interpretation and evidence limits.
10. [`docs/ACCEPTANCE.md`](docs/ACCEPTANCE.md) — auditable PO-1 through PO-11 completion matrix and V1.5 release gate.
11. [`docs/REPRODUCTION_RUNBOOK.md`](docs/REPRODUCTION_RUNBOOK.md) — blind independent-human PO-9 signoff protocol.

For V1.6 semantic work, also read:

12. [`docs/V1.6_SCOPE.md`](docs/V1.6_SCOPE.md) — current semantic-judge scope, authority boundaries, adapter status, and calibration requirements.
13. [`docs/V1.6_ACCEPTANCE.md`](docs/V1.6_ACCEPTANCE.md) — implementation-complete versus empirical-validation-pending status and merge interpretation.
14. [`docs/V1.6_EVALUATION_PLAN.md`](docs/V1.6_EVALUATION_PLAN.md) — frozen hosted/local transport, model-admission, prompt provenance, blinding, repetition, calibration, and validation protocol.
15. [`docs/V1.6_REAL_MODEL_RUNBOOK.md`](docs/V1.6_REAL_MODEL_RUNBOOK.md) — procedural hosted/local Tier-0 real-model execution and evidence-capture workflow.
16. [`docs/adr/0015-semantic-fail-propagation-vs-review.md`](docs/adr/0015-semantic-fail-propagation-vs-review.md) — preregistered Proposed decision framework for semantic FAIL authority.
17. [`docs/adr/0017-semantic-judge-isolation.md`](docs/adr/0017-semantic-judge-isolation.md) — isolated semantic-judge execution contract.

## Relation to evaluation practice

TRACE-Well begins after an evaluation obligation has been specified. It presupposes rather than replaces error-analysis-driven criteria selection and domain-expert adjudication.

See [`docs/RELATION_TO_PRACTICE.md`](docs/RELATION_TO_PRACTICE.md).

## Repository gates

Changes are gated by two separate CI jobs:

1. **Deterministic V1.5 Gate** — fresh checkout, Python 3.11 setup, dependency installation, `pytest`, and `python scripts/check_public_text.py`.
2. **PO-9 Clean-Runner Reproduction** — starts only after the deterministic gate succeeds, uses a separate fresh runner, executes `python scripts/reproduce_po9.py`, and uploads the `po9-reproduction-report` artifact.

The V1.6 semantic tests run under the deterministic test gate, while the inherited PO-9 job confirms that V1.6 changes have not broken the frozen V1.5 reproduction mechanism.

The clean-runner result does **not** substitute for the blind independent-human V1.5 signoff described above.

## Current status

### V1.5

The deterministic specification, execution path, benchmark corpus, evidence persistence, external-trace path, paired mitigation verification, CLI, automated proof coverage, and automated clean-runner reproduction are implemented and passing.

V1.5 is **Done**. Full **Proven** status remains blocked only by the blind independent-human PO-9 reproduction and operator self-attestation against the frozen V1.5 snapshot.

### V1.6 development

The semantic protocol, isolated mock execution, observable-evidence boundary, conservative integration, semantic evidence persistence, deterministic-only finding authority, local and dedicated-HF endpoint adapters, calibration harness, frozen initial evaluation plan, prompt/template provenance fields, preregistered ADR-0015 decision framework, and Tier-0 real-model execution tooling are implemented.

The implementation gate is complete. Empirical validation remains pending: no real hosted/local model execution has yet been completed or established as calibrated/validated. No semantic-only FAIL or finding authority has been granted.
