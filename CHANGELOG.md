# Changelog

All notable changes to TRACE-Well are documented here.

## Unreleased — V1.5

### Added

- canonical V1.5 specification stack;
- ADR registry and frozen implementation ADRs;
- deterministic domain models and canonical artifact hashing;
- observable trace helpers;
- deterministic reference-agent modes;
- construct-level deterministic evaluator;
- single BehaviorDeltaComparator with `PASS / FAIL / REVIEW` precedence;
- SafetyFinding lifecycle and paired mitigation verification;
- external-trace conformance and equivalence path;
- run manifests and persisted evidence bundles;
- CLI commands for pair execution, imported-trace evaluation, dev suite, and holdout;
- 9 distinct development CasePairs and 1 separate holdout pair;
- dedicated PO-7 inconsistent-specification fixture;
- PO-1 through PO-11 acceptance matrix;
- publication scanner and dependency-boundary CI controls;
- Apache-2.0 license, contribution guide, security policy, demo, roadmap, and reproducibility documentation.

### Evidence boundary

V1.5 supports prototype engineering evaluation evidence on controlled synthetic cases. It does not establish clinical validity, statistical generalization, comprehensive safety, regulatory compliance, or production readiness.

### Remaining release gate

Independent-operator clean-clone reproduction signoff for PO-9 remains procedural and must be recorded separately from automated CI evidence.
