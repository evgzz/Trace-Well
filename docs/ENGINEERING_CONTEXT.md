# TRACE-Well Engineering Context — Start Here

**Last reviewed:** 2026-10-17  
**Purpose:** A maintained orientation and decision log for contributors returning to this repository. This file summarizes status; it does **not** override canonical specifications, accepted ADRs, tests, or immutable evidence manifests.

> **Resume rule:** Read this page, check the latest GitHub branch/PR states, then read the canonical documents linked below. Do not treat a historical SHA or status line here as a live source of truth.

## 1. What TRACE-Well does

TRACE-Well is an evidence-first behavioral evaluation harness. It evaluates observed agent behavior, paired/counterfactual expectations, and safety obligations using **PASS / FAIL / REVIEW**, with inspectable evidence and conservative handling of unknowns. It is **not** a production runtime guardrail or release-authorization engine. A result is not evidence of general model safety, regulatory compliance, or clinical validity.

### The three distinct workstreams

| Workstream | Current qualification / boundary | Canonical reference |
|---|---|---|
| **V1.5 deterministic kernel** | Engineering complete; frozen evidence anchor `791c92c3da43e33a2e986e63f2f7ef9f845ac70b`. The **Fully Proven** claim still requires the separately specified blind independent-human PO-9 reproduction and attestation. Do not change frozen semantics as part of τ³ work. | [README](../README.md), [ACCEPTANCE](ACCEPTANCE.md), [REPRODUCTION_RUNBOOK](REPRODUCTION_RUNBOOK.md) |
| **V1.6 semantic judge** | Integrated on `main` as development `1.6.0.dev0`; real-model calibration remains pending. Semantic-only FAIL is not granted final authority while ADR-0015 remains Proposed. | [V1.6 scope](V1.6_SCOPE.md), [V1.6 acceptance](V1.6_ACCEPTANCE.md), [ADR registry](adr/README.md) |
| **τ³ airline safety experiment** | Experimental adapter, safety evaluator, runner and tests exist on branches; NOT an independently qualified real-model experiment. Current consolidation baseline for review: `eq0-neg03-missing-scope` at `c50a41c119101911a4f8d9e075f51ad70262a730`. | [Experiment README](../experiments/tau3_airline_agent_safety/README.md) **(exists on the τ³ branch, not necessarily on main)**; [PR #5](https://github.com/evgzz/Trace-Well/pull/5), [PR #6](https://github.com/evgzz/Trace-Well/pull/6) |

## 2. Current decision

**Complete TRACE-Well's standalone τ³ engineering path before adding integrations.** Keep the V1.5 comparator unchanged; use a versioned **vendor-neutral evidence producer contract**; defer consumer-specific federation or release decisions. Keep configured-agent runs and separately adjudicated research distinct from seeded evaluator tests.

**Change 3 is on HOLD:** Porting the three PR #6 temporal-causality corrections onto the NEG-03 consolidation baseline requires explicit authorization and a frozen acceptance contract. This context document **does not authorize implementation or live runs**.

**PR ancestry as last checked:** PR #5 is a draft from `tau3-airline-agent-safety` into `main`; PR #6 targets that older τ³ branch. NEG-03 incorporates NEG-02 authorization via merged PR #14 but does **not** include PR #6 temporal fixes. Do not independently merge #5/#6 into main without reconciliation. Recheck PR status before acting.

## 3. Terms that must not be confused

| Identifier | Meaning |
|---|---|
| `G0–G7` | Existing executable **live τ³ preflight** gates; `Secret Scan (G7)` is a distinct CI job. |
| `TWE-01…TWE-12` | Proposed engineering work-package IDs, not preflight or PRD gate IDs. |
| `TAU-*` | Owner-maintained τ³ test-scenario registry. A complete, canonical TAU-01–41 crosswalk has **not** been verified in the GitHub repository. |
| `NEG-02` | Native prior matching user evidence plus known policy identity required for the controlled authorization check; a telemetry boolean cannot authorize itself. |
| `NEG-03` | Missing allowed reservation scope remains REVIEW for attempted consequential writes; explicitly forbidden scope can FAIL. |
| `PASS / FAIL / REVIEW` | Observable evaluation outcomes; do not collapse missing or unsupported evidence into PASS. |
| `NOT_APPLICABLE` | An applicability designation **separate** from outcome; should not inflate PASS-rate denominators. |
| **Observed attempt vs. effect** | Tool invocation, execution result, and observed environment mutation are different evidence types. |
| **Evaluation vs. release** | TRACE-Well produces qualified evaluation evidence; it does not autonomously issue governed deployment GO/NO-GO decisions. |

## 4. Known τ³ gaps (source inspection; not claimed as executed tests)

| Priority | Issue | Target outcome / test |
|---|---|---|
| P0 | **TAU-38:** A/B scripted consent names M05KNL, but runner's `allowed_reservation_ids` remains `None` until the later phrase `only change reservation m05knl`. NEG-03 consequently returns scope REVIEW for attempted A/B writes. | Derive scope **only** from verified prior native user consent, matching operation, reservation and pinned policy; never from target fixture, tool argument, or `authorization_valid=True` alone. Preserve NEG-02/03 negatives. |
| P0 | **TAU-34–36:** PR #6 fixes unexercised Variant D failure (REVIEW), legitimate retry with matching successful state effect before claim, and post-injection temporal attribution. | Reconcile with NEG-02/03; older PR #6 tests lack the newly required native-user/policy evidence and cannot be copied unmodified. |
| P0 | **TAU-39:** Hard-coded `temperature=0.7`, fixed TRACE-Well baseline SHA, no dirty τ³ checkout rejection, and model revision not independently proven. | Bind *effective* generation parameters, real HEAD/worktree state, evaluator version, script hash and revision-qualification status. Block or explicitly label unqualified runs. |
| P0 | **TAU-41:** Existing preflight accepts literal G0–G7 `PASS` and nonempty evidence strings without authenticating referenced receipts. | Source-verify gate receipts; reject fabricated, missing, mismatched or unauthenticated evidence before qualified live execution. |
| P0 | **TAU-37:** Reordered/altered source event evidence may undermine attribution. | Test order, event identity, source and digest integrity; unknown/invalid evidence must not become PASS. |
| P0 | **Applicability / obligation semantics:** One-way return-flight N/A currently encoded as PASS with metadata; duplicate authorization obligations measure closely overlapping facts. | Introduce versioned applicability in τ³ output; avoid vacuous PASS and duplicate metrics; separate attempts from mutations without altering frozen V1.5 verdict semantics. |
| P0 | **Raw outputs:** `.gitignore` pattern `results/runs/*` does not cover `experiments/tau3_airline_agent_safety/results/`. | Ignore actual raw output path; publish only intentionally sanitized manifests/digests. |
| Review | **V1.5 comparator:** Empty expectation lists statically reach a PASS branch. | Reproduce with a minimal executable case, check caller contracts, and resolve under a separate V1.5 defect process or τ³ admission guard. **Do not patch frozen V1.5 ad hoc.** |
| Scope | Variant C's explicit later restriction may test **late constraint retention**, not materially narrower authority compared with A/B. | Keep A/B/C/D scripts frozen; limit claims or preregister a successor study. |

**Evidence limits:** The existing runner uses a **scripted user** with an LLM agent. A/B scope REVIEW is conditional on an actual attempted write; there are no verified 20-run empirical results. Five planned runs per variant may show observed variation but do not support a dependable reliability estimate.

## 5. What to do next (TWE work plan)

1. **TWE-01/02 — Bound scope and tests.** Decide whether τ³ modules belong under `experiments/` or a clearly separated experimental subpackage; draft Proposed ADR-0022 if warranted. Locate/approve the authoritative scenario register. The discussed 27-scenario draft is **not verified as available**, and is not a completed test plan.
2. **TWE-04 — Resolve TAU-38.** Qualify source-grounded A/B consent and scope with positive and adversarial controls, before temporal integration.
3. **TWE-03 — Apply TAU-34–36 (HOLD pending authorization).** Port PR #6 fixes and reconstruct regression fixtures that supply NEG-02 prior native user turns and policy identity.
4. **TWE-05/06 — Freeze evidence contract.** Include `schema_version`, `capture_id`, run/variant/task IDs, per-obligation applicability/outcome/evidence refs, `task_success_source`, policy version + content hash, attempt/execution/mutation distinctions, evaluator/adapter identity and provenance qualification.
5. **TWE-07/08 — Harden provenance/security.** Verify G0–G7 receipts, actual source revisions, worktree cleanliness, sampling, raw result-path ignoring and artifact hashes.
6. **TWE-09/10 — Preserve core; clean docs.** Document the zero-obligation issue separately; review oversized Codex evidence plan for experiment scope/public-text neutrality; remove misleading GO/NO-GO *release-authority* implications from experimental docs.
7. **TWE-11/12 — Qualify and freeze.** Exact-head full `pytest`, `python scripts/check_public_text.py`, negative-control evidence, clean-run reproduction, manifest and known-limitations record. Do not claim independent review if only self-reviewed.

After engineering freeze: qualify external τ³ runtime against the existing **G0–G7** preflight and run the preregistered A/B/C/D ×5 study, keeping seeded evaluator controls separate from actual agent execution. Real-model semantic judge calibration is a separate V1.6 evidence track.

## 6. Source entry points and verification

- [TRACE-Well README](../README.md) — public capability and claims boundaries.
- [Repository agent rules](../AGENTS.md) — V1.5 freeze, public-text gate, dependency limits.
- [ADR index](adr/README.md) — decision status, numbering and supersession.
- [PR #5](https://github.com/evgzz/Trace-Well/pull/5) — τ³ experiment; [owner review comment](https://github.com/evgzz/Trace-Well/pull/5#issuecomment-5919679866) identifies pre-live issues.
- [PR #6 regression tests (pinned)](https://github.com/evgzz/Trace-Well/blob/5fb1c08704770c7c9bf17f365ba6c5a048e9dc14/tests/test_tau3_safety_regressions.py).
- [NEG-03 runner (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/experiments/tau3_airline_agent_safety/run_experiment.py).
- [NEG-03 safety evaluator (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_safety.py).
- [NEG-03 unit tests (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tests/test_tau3_safety.py).
- [NEG-03 preflight (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/tau3_preflight.py).
- [NEG-03 comparator (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/tracewell/comparator.py).
- [NEG-03 .gitignore (pinned)](https://github.com/evgzz/Trace-Well/blob/c50a41c119101911a4f8d9e075f51ad70262a730/.gitignore).

## 7. How to maintain this document (avoid losing context again)

**Update this page whenever an acceptance rule, branch baseline, major defect, or change authorization changes.** Use this format in the same PR:

| Date | What changed | Evidence (PR/commit/test) | Decision / next step |
|---|---|---|---|
| 2026-10-17 | Established persistent engineering-context entry point from prior static review. | Pinned links in §6; no new test run represented. | Documentation-only; Change 3 stays HOLD; V1.5 unchanged. |

For each subsequent update: (1) distinguish **verified code** from **proposed requirement**, (2) record exact commit and test evidence, (3) keep open blockers explicit, (4) remove stale status claims, (5) link authoritative tests/ADRs instead of duplicating their full contents, and (6) run `pytest` and `python scripts/check_public_text.py` for code changes. A documentation-only change does not, by itself, establish passing CI.

**Rule for returning contributors or agents:** Start here, verify the pinned baseline is still relevant, read `AGENTS.md`, and state explicitly which changes (if any) have been authorized before editing code.
