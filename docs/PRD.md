# TRACE-Well V1.5 — Product Requirements Document

## 1. Single V1.5 claim

On designed counterfactual pairs, TRACE-Well determines whether an agent made the required behavioral change, held required invariants, whether mitigation survives both sides, and whether the evaluator must abstain as `REVIEW` when specification/evidence is not reliable enough for deterministic judgment — with evidence an independent third party can reproduce.

This is a **mechanism/existence proof**, not a coverage, clinical-validity, or statistical-generalization claim.

## 2. Proof obligations

### PO-1 — Required change detected
When the required canonical→perturbed behavioral transition occurs, the comparator reports the expected change as satisfied.

### PO-2 — Missing required change detected
When the required transition does not occur or reaches the wrong target value, the comparator reports `FAIL`.

### PO-3 — Invariant violation detected
When behavior that must remain stable changes or violates an `equals` invariant, the comparator reports `FAIL`.

### PO-4 — Invariant preservation confirmed
When a required invariant holds across both conditions, it is reported as satisfied.

### PO-5 — Underreaction and overreaction both detected
The benchmark demonstrates both:
- failure to escalate when required; and
- unnecessary escalation in a benign condition.

### PO-6 — Trajectory-dependent revision evaluated
A scripted multi-turn pair demonstrates both correct late-context revision and failure to revise after an explicit fixture-defined material state change.

### PO-7 — REVIEW is reachable and terminal offline
A deliberately inconsistent specification deterministically produces `REVIEW`. `REVIEW` never silently becomes `PASS`.

### PO-8 — Mitigation survives both conditions
Verification reruns both members of the same CasePair under the mitigation and closes only when the explicit closure criterion holds.

### PO-9 — Independent deterministic reproduction
Equivalent authored representations resolve to the same effective artifact identity; meaningful semantic changes produce a different identity; all evaluation-relevant execution configuration is explicit; deterministic reruns reproduce the same conclusion without relying on unstored author knowledge.

### PO-10 — External execution preserves evaluation semantics
Conforming externally produced traces enter the same evaluator/comparator path as built-in traces and yield equivalent verdict semantics; malformed traces are rejected.

### PO-11 — Public artifact controls function independently
A fresh clone can run the generic public-text scanner and CI without private local files. The scanner's inability to prove absence of arbitrary sensitive proper nouns is explicitly documented.

## 3. Directionality requirements

The proof set must contain both success and failure/control directions where relevant.

Examples:
- expected change succeeds / expected change fails;
- invariant preserved / invariant violated;
- escalation underreaction / overreaction;
- late-context revision / failure-to-revise;
- valid spec / deliberately inconsistent spec;
- mitigation before / after paired verification.

A happy-path-only corpus is insufficient.

## 4. Component-to-proof mapping

| Component | Primary POs |
|---|---|
| CasePair + ExpectedChange/ExpectedInvariant | PO-1, PO-2, PO-3, PO-4 |
| Deterministic reference agent | PO-1, PO-2, PO-4, PO-5, PO-6 |
| Deterministic evaluator | PO-1 through PO-7 |
| BehaviorDeltaComparator | PO-1 through PO-7 |
| Findings + paired verification | PO-8 |
| Canonicalization + RunManifest | PO-9 |
| External trace conformance path | PO-10 |
| Public-text scanner + CI | PO-11 |

## 5. Scope kill-switch

Before implementing a V1.5 feature, ask:

> Which PO cannot be demonstrated correctly without this?

If there is no answer, defer it unless needed to preserve an accepted interface boundary.

## 6. Non-metrics

The canonical non-metrics list is owned by `docs/MVP_SCOPE.md §9` and is not duplicated here.

## 7. Proven gate

V1.5 is **Proven** only when PO-1 through PO-11 have evidence in their required directions.

## 8. Done gate

V1.5 is **Done** only when the clean-clone engineering gates pass, including installation, tests, public-text scan, CLI/evidence paths, and documentation.

Both are required:

```text
MVP complete = Proven AND Done
```

## 9. Principal ADRs

See `docs/PO_ADR_MAP.md` for the complete enabling map. Principal decisions include paired evaluation semantics, construct-level results, CasePair authority, deterministic reference-agent taxonomy, paired verification, reproducibility configuration, public-repository controls, external traces, and canonical artifact normalization.
