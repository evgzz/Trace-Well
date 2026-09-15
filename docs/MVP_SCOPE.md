# TRACE-Well V1.5 — MVP Scope

> Governing scope boundary for the deterministic open-source V1.5 mechanism proof.

## 1. Governing terminology

TRACE-Well V1.5 is a **paired/counterfactual behavioral evaluation harness**.

Repository language uses **evaluation**, not assurance. Broader product concepts may use other terminology outside this repository, but V1.5 claims remain bounded to evaluation evidence.

> **V1.5 proves the primitive exists and is reproducible; it does not prove the primitive is sufficient.**

## 2. Mission

Given a controlled CasePair, TRACE-Well executes or imports both conditions, evaluates observable construct-level behavior, compares the observed delta against explicit required changes and invariants, emits `PASS`, `FAIL`, or `REVIEW`, preserves evidence/provenance, and supports paired mitigation verification.

## 3. In scope

V1.5 includes:

- typed domain objects for Case, CasePair, EvaluationContract, ExpectedChange, ExpectedInvariant, Trace, EvaluationResult, BehaviorDeltaResult, SafetyFinding, and RunManifest;
- canonical artifact normalization and SHA-256 `artifact_digest`;
- deterministic reference-agent execution;
- first-class conforming external-trace input;
- deterministic-first construct evaluators;
- one shared BehaviorDeltaComparator;
- explicit specification-consistency handling;
- `PASS / FAIL / REVIEW` verdicts;
- paired mitigation verification rerunning both conditions;
- file-based evidence and reproducibility manifests;
- 8–12 distinct synthetic CasePairs across four scenario families;
- benign and distractor controls, underreaction, overreaction, and holdout mechanics;
- credential-free CI and publication scanning.

## 4. Scenario families

1. Context Sensitivity
2. Contradiction and Uncertainty
3. Tool Authority
4. Scripted Late-Context Multi-Turn Revision

These provide **mechanism breadth**, not a comprehensive taxonomy or coverage claim.

## 5. Data boundary

Synthetic data only. No PHI, live patient data, production clinical records, secrets, or credentials are required.

## 6. Holdout boundary

A small holdout CasePair set is excluded from ordinary `run-suite` execution and exposed only through an explicit holdout path.

The holdout tests a narrow engineering property. It does not establish statistical generalization or external validity.

## 7. Explicit non-goals

V1.5 is not:

- a general model benchmark or leaderboard;
- a production safety platform;
- a clinical decision-support system;
- a medical device;
- a release-governance or approval platform;
- a multi-agent framework;
- a statistical evaluation study;
- a validated semantic-judge system;
- an adaptive user simulator;
- a production observability platform.

## 8. Release-decision boundary

TRACE-Well may produce evidence useful to a broader release process. V1.5 does not issue organizational ship/no-ship authorization.

## 9. Non-metrics

V1.5 does not use the small designed corpus to report population-style metrics such as:

- accuracy percentage;
- F1;
- AUROC/AUPRC;
- statistical significance;
- confidence intervals for population reliability;
- model rankings or comparison scores;
- semantic-judge/human agreement rates;
- clinical performance percentages.

V1.5 outputs per-obligation `PASS / FAIL / REVIEW`, artifact identities, evidence references, and reproducibility provenance.

## 10. Users

Primary public personas are:

- evaluation engineer;
- repository maintainer;
- independent reproducer.

## 11. Proven versus Done

**Proven** means the PRD proof obligations have been demonstrated in their required positive, failure, control, REVIEW, verification, and reproducibility directions.

**Done** means the repository engineering gates pass: clean installation, tests, scanner, CLI/evidence paths, documentation, and CI.

```text
Done = true, Proven = false
```

is not MVP completion.

## 12. Scope test

Before adding V1.5 work, ask:

> Which PRD proof obligation requires this?

If none does, place it in roadmap/future work unless it is necessary to keep an accepted interface extensible.

## 13. Evidence class

Approved framing:

> **Prototype engineering evaluation evidence.**

## 14. Claims ceiling

V1.5 does **not** establish:

- clinical validity;
- clinical efficacy;
- patient safety;
- regulatory compliance;
- comprehensive AI/model safety;
- population-level reliability;
- statistical generalization;
- production readiness.

Do not describe V1.5 as clinically proven, safe AI, validated medical AI, regulatory compliant, production ready, or as guaranteeing safety.

## 15. Governing rule

> **A successful V1.5 release demonstrates a reproducible evaluation mechanism on controlled synthetic cases. It does not establish that the mechanism or evaluated system is sufficient for real-world clinical or production use.**
