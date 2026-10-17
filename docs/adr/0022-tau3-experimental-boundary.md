# ADR-0022 — τ³ Experimental Boundary and Evidence-Producer Contract

**Status:** Proposed (not an approved architecture decision)  
**Date:** 2026-10-17  
**Work package:** TWE-01  
**Decision owner:** Repository maintainers; approval pending  
**Related:** ADR-0002, ADR-0008, ADR-0016, ADR-0019 (no hidden chain-of-thought), ADR-0020, ADR-0021 (provenance binding), and [engineering context](../ENGINEERING_CONTEXT.md)

## Context and problem

The τ³ airline runner is under `experiments/tau3_airline_agent_safety/run_experiment.py` and describes the external benchmark as an experiment-only dependency. The τ³ normalization adapter, task-specific safety evaluator, and preflight live under `tracewell/tau3_adapter.py`, `tracewell/tau3_safety.py`, and `tracewell/tau3_preflight.py` on the NEG-03 branch. This layout can imply that an experimental, task-15-specific policy is general-purpose core policy.

The frozen V1.5 deterministic comparator and PO-9 claims must not be changed by τ³ integration. `main` contains V1.6 semantic-judge integration, including ADR-0021 provenance-binding work not present on the τ³ branch. As of 2026-10-17, `main...eq0-neg03-missing-scope` **diverged**: the τ³ branch was 36 commits ahead and 18 behind `main` (following documentation PR #15). A passing test suite on either branch alone does not qualify a future consolidated tree.

## Proposed decision — for maintainers to approve or amend

1. **Experiment ownership.** τ³ task-15 fixtures, scripts, injected content, benchmark-derived authorization matcher, flight/reservation oracles, model settings, and G0–G7 live-experiment preflight are experimental code. They must not redefine V1.5 comparator semantics or V1.6 semantic-judge authority.
2. **Compatibility before physical relocation.** Preserve the explicitly enumerated public imports in the seam contract below until a separately approved compatibility plan replaces them. Experimental code may later move under `experiments/` or an explicitly experimental package, but a relocation decision **must be made before TWE-12 engineering freeze** and must include import, wheel-content and test evidence. **This Proposed ADR does not approve code moves.**
3. **Packaging and runtime dependencies.** The existing `pyproject.toml` specifies `[tool.setuptools.packages.find] include = ["tracewell*"]`, which packages `tracewell.tau3_adapter`, `tracewell.tau3_safety`, and `tracewell.tau3_preflight` in the **base wheel today**, even though `tau2` is an optional experiment dependency. Proposed transitional policy: preserve those module paths and their base-wheel inclusion until a separately authorized migration; explicitly label them experimental, not general-purpose evaluator APIs. Base TRACE-Well import/install, deterministic CI, and V1.6 mock tests must not require installed τ³/tau2-bench, network/model access, or credentials. Before TWE-12, explicitly decide **retain with experimental namespace and compatibility** versus **exclude or separately distribute with a tested migration**; inspect the built wheel and verify both the module manifest and dependency boundary.
4. **Vendor-neutral producer contract.** Before freeze, qualify versioned output with `schema_version`, `capture_id`, run/task/variant IDs, an explicit `applicability` separate from `verdict`, source evidence refs, `task_success_source`, policy version and content SHA, the observed tool attempt/execution/effect sequence, script digest, evaluator/adapter versions, model revision and effective decoding configuration, source HEAD/worktree state, and verification status. These are **requirements**, not a statement that the fields already exist.
5. **Conservative evidence and authority.** Missing/unverifiable data cannot become PASS. **D10's proposed encoding rule:** `applicability=NOT_APPLICABLE` entails **no obligation verdict** (a null/absent field, not `PASS`), and that obligation is excluded from applicable-outcome denominators. `APPLICABLE` retains explicit PASS/FAIL/REVIEW semantics; `UNDETERMINED` cannot be silently counted as PASS. This is a **τ³ producer-schema proposal**, not a change to the frozen V1.5 `Verdict` enum. Separate tool attempts from actual state changes and independent effect observations. TRACE-Well produces evaluation evidence, not governed production GO/NO-GO authorization.
6. **Experimental design limits.** The current runner drives an LLM agent with a fixed scripted user; an orchestrator seed does not prove seeded LLM decoding. Task-15 variant C adds an explicit late constraint, but current scripts do not automatically establish a material reduction of previously authorized actions.
7. **Source and test discipline.** Current branch-positive tests do not prove the consolidated head. Merge/rebase sequencing must reconcile `main`'s V1.6/ADR-0021 implementation, NEG-02/03, and the still-unmerged PR #6 temporal fixes. Run tests and publication scans against the **resulting exact SHA**.
8. **Instrumentation and provenance.** Recording synthetic agent messages/tool outcomes must observe ADR-0019's ban on requesting or persisting hidden chain-of-thought. Carry forward ADR-0021's distinction between artifact identity and effective execution configuration **as a design requirement**, without claiming that its V1.6 semantic-judge bindings already qualify τ³ runner telemetry or hosted model revisions.

## Proposed compatibility seam (acceptance contract, not yet implemented)

These explicit module-qualified names are the **candidate public import surface** during consolidation; none of the existing `tracewell.tau3_*` files currently defines its own `__all__`. A maintainer must approve and implement a per-module `__all__` reflecting this list and provide an executable compatibility test; `tracewell.__all__` does **not** need to re-export task-15 helpers.

| Module-qualified import path | Candidate `__all__` exports to preserve in a compatibility test |
|---|---|
| `tracewell.tau3_adapter` | `Tau3AdapterError`, `Tau3NormalizedEvent`, `Tau3NormalizedTrajectory`, `normalize_tau3_simulation`, `to_tracewell_trace` |
| `tracewell.tau3_safety` | `ObligationResult`, `Tau3SafetyEvaluation`, `evaluate_airline_safety`, `AUTHORIZATION_POLICY_VERSION` |
| `tracewell.tau3_preflight` | `Tau3PreflightError`, `sha256_file`, `load_and_validate_preflight`, `REQUIRED_GATES` |

**Contract test requirement:** an import-only, credential-free test must import every advertised symbol; assert `module.__all__` equals the approved list; instantiate or invoke safe representative paths; and confirm that importing base `tracewell` plus each module without `tau2` present causes no dependency resolution or external access. A **built-wheel smoke test** must verify the desired module inclusion/exclusion and package metadata, not infer wheel contents from a source-tree editable install. An approved relocation must either maintain these imports through tested shims or explicitly version a breaking API change with deprecation and migration evidence.

**Relocation / packaging decision gate:** resolve physical location and base-wheel distribution **before TWE-12**. If unresolved, record **TWE-01 / TWE-12 BLOCKED**, not an indefinite `DEFER`. Do not silently rename or move modules in the docs PR. The proposed seam is limited to τ³ experimental qualification; no general-purpose authority or stabilized public API is claimed until accepted.

## Alternatives

| Option | Benefit | Risk | Recommendation |
|---|---|---|---|
| Treat current `tracewell/tau3_*` as production core | Few imports change | Implicitly elevates task-15 oracles and third-party benchmark coupling | Reject |
| Immediately move modules into `experiments/` | Clean namespace | Broad import/churn risk before evaluator defects and branch reconciliation | Defer |
| Experimental ownership with stable import compatibility and documented seam | Smallest safe change; separable producer contract | Requires clear documentation until refactor | **Proposed** |

## Definition of done / validation

**TWE-01 is DONE only after** maintainers explicitly accept or amend this ADR, choose module ownership/location and **base-wheel inclusion**, approve and implement per-module `__all__`, pass an import/compatibility test and wheel-content smoke test on the consolidated exact head, and confirm frozen V1.5 authority is unchanged. **Relocation must be explicitly decided before TWE-12.** A file marked `Proposed` is **NOT** an approved decision. Executable compatibility tests and exact-head CI are required when code changes occur.

**Current status:** **PROPOSED / DECISION PENDING**. No τ³ implementation, merger, relocation or Change 3 authorization is performed by this documentation change.

## Evidence

- [Main context and freeze rules](../ENGINEERING_CONTEXT.md)
- [Pinned NEG-03 runner](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/experiments/tau3_airline_agent_safety/run_experiment.py)
- [Pinned NEG-03 adapter](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_adapter.py)
- [Pinned NEG-03 safety evaluator](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_safety.py)
- [Pinned NEG-03 preflight](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_preflight.py)
- [Main package discovery rule](../../pyproject.toml); [ADR-0019](0019-no-hidden-chain-of-thought.md); [ADR-0021](0021-judge-provenance-binding.md)
- [PR #5](https://github.com/evgzz/Trace-Well/pull/5), [PR #6](https://github.com/evgzz/Trace-Well/pull/6), [PR #14](https://github.com/evgzz/Trace-Well/pull/14)

## Decision log

| Date | Event | Status |
|---|---|---|
| 2026-10-17 | ADR prepared to avoid accidental elevation of experiment-specific logic and premature dependency integration | **Proposed; awaiting maintainer acceptance; reviewer status: self-review** |
| 2026-10-17 | Amendment: explicit import/`__all__` seam, wheel-packaging truth, pre-TWE-12 relocation trigger and ADR-0019/0021 provenance constraints | **Proposed; no implementation or independent acceptance** |
