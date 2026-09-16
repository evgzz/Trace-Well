# TRACE-Well V1.5 — Acceptance Matrix

> Single auditable entry point for the PRD proof obligations and repository completion gates.

## Status vocabulary

- **Automated** — demonstrated by committed tests in credential-free CI.
- **Procedural** — requires a documented human/operator procedure in addition to automated checks.
- **Pending** — evidence has not yet been completed.

A green CI run proves the automated checks only. It does not by itself satisfy a procedural proof obligation.

## Proof obligations

| PO | Requirement | Primary executable evidence | Status |
|---|---|---|---|
| PO-1 | Detect required behavioral change when it occurs | `tests/test_suite.py`, `tests/test_execution_and_comparator.py` | Automated |
| PO-2 | Detect missing required behavioral change | seeded failure modes in `tests/test_suite.py` | Automated |
| PO-3 | Detect invariant violation | `auth-002 + violate_tool_boundary` in `tests/test_suite.py` | Automated |
| PO-4 | Confirm invariant preservation | `ctx-003` and invariant-preservation assertions in suite/comparator tests | Automated |
| PO-5 | Detect escalation underreaction and overreaction | `ctx-001` under `ignore_context` and `always_escalate` | Automated |
| PO-6 | Detect trajectory-dependent revision / failure-to-revise | `late-001` and `late-002` in `tests/test_suite.py` | Automated |
| PO-7 | Reach terminal offline `REVIEW` for unreliable specification | `cases/fixtures/po7-spec-inconsistent.yaml`, `tests/test_po7_fixture.py` | Automated |
| PO-8 | Verify mitigation across both conditions | `tests/test_lifecycle.py` | Automated |
| PO-9 | Reproduce deterministic evidence without unstored author knowledge | canonicalization/manifest/rerun tests plus clean-clone procedure | **Procedural — independent operator signoff pending** |
| PO-10 | Preserve evaluation semantics for conforming external traces and reject malformed traces | `tests/test_external.py`, `tests/test_cli.py` | Automated |
| PO-11 | Public artifact controls work independently with scanner limitation explicit | `tests/test_dependency_boundary.py`, `scripts/check_public_text.py`, CI | Automated |

## Benchmark proof directions

The development inventory contains **9 distinct CasePair specifications** and **18 deterministic executions**. Agent modes are run configuration and do not increase the pair count.

Required directions are pinned as follows:

- expected-change success and failure;
- invariant preservation and violation;
- underreaction and overreaction;
- late-context revision and failure-to-revise;
- Tool Authority success/failure;
- a separate holdout path;
- a dedicated PO-7 inconsistent-specification fixture producing global `REVIEW`.

## Done gate

The repository is **Done** only when all of the following are true:

```text
[ ] clean installation path documented and verified
[ ] pytest passes in credential-free CI
[ ] public-text scan passes in CI
[ ] dependency-boundary test passes
[ ] real CLI commands documented
[ ] evidence files and manifests persist correctly
[ ] README / DEMO match implemented commands
[ ] LICENSE present
[ ] CONTRIBUTING.md present
[ ] SECURITY.md present
[ ] CHANGELOG.md present
[ ] independent clean-clone reproduction procedure documented
```

## Proven gate

The repository is **Proven** only when:

```text
[ ] PO-1 automated evidence passes
[ ] PO-2 automated evidence passes
[ ] PO-3 automated evidence passes
[ ] PO-4 automated evidence passes
[ ] PO-5 automated evidence passes
[ ] PO-6 automated evidence passes
[ ] PO-7 automated REVIEW evidence passes
[ ] PO-8 paired mitigation verification passes
[ ] PO-9 deterministic automated evidence passes
[ ] PO-9 independent-operator reproduction is signed off
[ ] PO-10 external trace equivalence/conformance passes
[ ] PO-11 publication controls pass
```

## Current interpretation rule

Until the independent-operator PO-9 procedure is completed, the repository may be described as having **automated proof coverage for PO-1–PO-11 with PO-9 procedural signoff pending**.

Do not collapse that distinction into “fully Proven.”
