# ADR-0022 — τ³ Experimental Boundary and Evidence-Producer Contract

**Status:** Proposed (not an approved architecture decision)  
**Date:** 2026-10-17  
**Work package:** TWE-01  
**Decision owner:** Repository maintainers; approval pending  
**Related:** ADR-0002, ADR-0008, ADR-0016, ADR-0020, and [engineering context](../ENGINEERING_CONTEXT.md)

## Context and problem

The τ³ airline runner is under `experiments/tau3_airline_agent_safety/run_experiment.py` and describes the external benchmark as an experiment-only dependency. The τ³ normalization adapter, task-specific safety evaluator, and preflight live under `tracewell/tau3_adapter.py`, `tracewell/tau3_safety.py`, and `tracewell/tau3_preflight.py` on the NEG-03 branch. This layout can imply that an experimental, task-15-specific policy is general-purpose core policy.

The frozen V1.5 deterministic comparator and PO-9 claims must not be changed by τ³ integration. `main` contains V1.6 semantic-judge integration, including ADR-0021 provenance-binding work not present on the τ³ branch. As of 2026-10-17, `main...eq0-neg03-missing-scope` **diverged**: the τ³ branch was 36 commits ahead and 18 behind `main` (following documentation PR #15). A passing test suite on either branch alone does not qualify a future consolidated tree.

## Proposed decision — for maintainers to approve or amend

1. **Experiment ownership.** τ³ task-15 fixtures, scripts, injected content, benchmark-derived authorization matcher, flight/reservation oracles, model settings, and G0–G7 live-experiment preflight are experimental code. They must not redefine V1.5 comparator semantics or V1.6 semantic-judge authority.
2. **Compatibility before physical relocation.** Keep existing `tracewell.tau3_*` import paths working during acceptance analysis. A later separately authorized refactor may relocate code under `experiments/` or a clearly named experimental subpackage, with imports, version bindings and tests maintained. **This ADR proposes a boundary; it does not itself approve code moves.**
3. **No base-runtime dependency.** Base TRACE-Well install, deterministic CI, and V1.6 mock tests must not require an installed τ³/tau2-bench, network/model access, or credentials.
4. **Vendor-neutral producer contract.** Before freeze, qualify versioned output with `schema_version`, `capture_id`, run/task/variant IDs, an explicit `applicability` separate from `verdict`, source evidence refs, `task_success_source`, policy version and content SHA, the observed tool attempt/execution/effect sequence, script digest, evaluator/adapter versions, model revision and effective decoding configuration, source HEAD/worktree state, and verification status. These are **requirements**, not a statement that the fields already exist.
5. **Conservative evidence and authority.** Missing/unverifiable data cannot become PASS. Do not score `NOT_APPLICABLE` as an applicable PASS. Separate tool attempts from actual state changes and independent effect observations. TRACE-Well produces evaluation evidence, not governed production GO/NO-GO authorization.
6. **Experimental design limits.** The current runner drives an LLM agent with a fixed scripted user; an orchestrator seed does not prove seeded LLM decoding. Task-15 variant C adds an explicit late constraint, but current scripts do not automatically establish a material reduction of previously authorized actions.
7. **Source and test discipline.** Current branch-positive tests do not prove the consolidated head. Merge/rebase sequencing must reconcile `main`'s V1.6/ADR-0021 implementation, NEG-02/03, and the still-unmerged PR #6 temporal fixes. Run tests and publication scans against the **resulting exact SHA**.

## Alternatives

| Option | Benefit | Risk | Recommendation |
|---|---|---|---|
| Treat current `tracewell/tau3_*` as production core | Few imports change | Implicitly elevates task-15 oracles and third-party benchmark coupling | Reject |
| Immediately move modules into `experiments/` | Clean namespace | Broad import/churn risk before evaluator defects and branch reconciliation | Defer |
| Experimental ownership with stable import compatibility and documented seam | Smallest safe change; separable producer contract | Requires clear documentation until refactor | **Proposed** |

## Definition of done / validation

**TWE-01 is DONE only after** maintainers explicitly accept or amend this ADR, choose module ownership/location, identify the long-term import/seam contract, and confirm frozen V1.5 authority is unchanged. A file marked `Proposed` is **NOT** an approved decision. Executable compatibility tests and exact-head CI are required when a code change occurs.

**Current status:** **PROPOSED / DECISION PENDING**. No τ³ implementation, merger, relocation or Change 3 authorization is performed by this documentation change.

## Evidence

- [Main context and freeze rules](../ENGINEERING_CONTEXT.md)
- [Pinned NEG-03 runner](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/experiments/tau3_airline_agent_safety/run_experiment.py)
- [Pinned NEG-03 adapter](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_adapter.py)
- [Pinned NEG-03 safety evaluator](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_safety.py)
- [Pinned NEG-03 preflight](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_preflight.py)
- [PR #5](https://github.com/evgzz/Trace-Well/pull/5), [PR #6](https://github.com/evgzz/Trace-Well/pull/6), [PR #14](https://github.com/evgzz/Trace-Well/pull/14)

## Decision log

| Date | Event | Status |
|---|---|---|
| 2026-10-17 | ADR prepared to avoid accidental elevation of experiment-specific logic and premature dependency integration | **Proposed; awaiting maintainer acceptance** |
