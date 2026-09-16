# TRACE-Well V1.5 — Acceptance Matrix

> Single auditable entry point for the PRD proof obligations and repository completion gates.

## Status vocabulary

- **Automated** — demonstrated by committed tests in credential-free CI.
- **Clean-runner reproduced** — the tracked PO-9 reproduction script completed successfully on a fresh GitHub Actions checkout and produced a machine-readable report artifact.
- **Procedural** — requires a documented human/operator procedure in addition to automated checks.
- **Pending** — evidence has not yet been completed.

A green CI run proves the automated checks and clean-runner procedure. It does not by itself establish that an independent human/operator reproduced the result without author knowledge.

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
| PO-9 | Reproduce deterministic evidence without unstored author knowledge | canonicalization/manifest/rerun tests, `scripts/reproduce_po9.py`, clean-runner artifact, independent runbook | **Clean-runner reproduced; independent human/operator signoff pending** |
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

## Automated clean-runner reproduction

CI executes:

```bash
python scripts/reproduce_po9.py
```

on a fresh checkout after installation and the ordinary repository gates.

The verifier asserts:

```text
PASS reproduction
FAIL reproduction + finding.json
REVIEW reproduction + no normal finding
mode-only artifact_digest equality
agent_mode provenance difference
9 distinct development CasePairs
18 deterministic development executions
9 PASS / 9 FAIL / 0 REVIEW
1 explicit holdout CasePair / PASS
```

It writes and uploads:

```text
results/reproduction/po9-reproduction-report.json
```

The report explicitly records:

```text
operator_class: automated_clean_runner
independent_human_operator_signoff: false
```

This is stronger than unit-test-only evidence but intentionally does not impersonate independent-human reproduction.

## Done gate

The repository engineering/release surface is **Done** when all of the following are true:

```text
[x] clean installation path documented and verified in CI
[x] pytest passes in credential-free CI
[x] public-text scan passes in CI
[x] dependency-boundary test passes
[x] real CLI commands documented
[x] evidence files and manifests persist correctly
[x] README / DEMO match implemented commands
[x] LICENSE present
[x] CONTRIBUTING.md present
[x] SECURITY.md present
[x] CHANGELOG.md present
[x] independent clean-clone reproduction procedure documented
[x] automated clean-runner reproduction passes and report artifact is uploaded
```

Therefore the engineering/repository **Done** gate is satisfied.

## Proven gate

The repository is **Proven** only when:

```text
[x] PO-1 automated evidence passes
[x] PO-2 automated evidence passes
[x] PO-3 automated evidence passes
[x] PO-4 automated evidence passes
[x] PO-5 automated evidence passes
[x] PO-6 automated evidence passes
[x] PO-7 automated REVIEW evidence passes
[x] PO-8 paired mitigation verification passes
[x] PO-9 deterministic automated evidence passes
[x] PO-9 automated clean-runner reproduction passes
[ ] PO-9 independent-human/operator reproduction is signed off
[x] PO-10 external trace equivalence/conformance passes
[x] PO-11 publication controls pass
```

## Current interpretation rule

The repository is currently:

> **Done, with automated and clean-runner proof coverage across PO-1–PO-11; full Proven status remains blocked only by PO-9 independent-human/operator signoff.**

Do not collapse the clean-runner CI result into independent-human attestation.
