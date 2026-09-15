# TRACE-Well V1.5 — Limitations

> Defines the evidentiary limits of TRACE-Well V1.5.  
> For the canonical non-metrics list, see `docs/MVP_SCOPE.md §9`.  
> For the canonical claims ceiling, see `docs/MVP_SCOPE.md §14`.

## 1. Approved interpretation

TRACE-Well V1.5 produces:

> **Prototype engineering evaluation evidence.**

It demonstrates whether a small paired/counterfactual evaluation mechanism behaves correctly on controlled designed cases.

It does not establish that the mechanism is sufficient for broader clinical, statistical, regulatory, or production use.

## 2. The defining limitation

> **V1.5 has not validated the human-adjudication or semantic-evaluation layer required for ambiguous real-world behavioral evaluation.**

The MVP deliberately demonstrates the deterministic control flow first: explicit paired specifications, observable traces, mechanically evaluable constructs, verdict discipline, reproducibility, and paired mitigation verification.

The authority layer required for broader real-world use remains deferred. V1.5 does not establish that:

- qualified human raters would agree on ambiguous constructs;
- automated semantic judges are valid substitutes for expert judgment;
- decision thresholds are clinically meaningful;
- the deterministic constructs are sufficient for consequential real-world evaluation.

This is the principal limitation of the current evidence.

## 3. What a PASS means

A V1.5 `PASS` means only:

> The observed canonical and perturbed executions satisfied the explicit CasePair expectations and required invariants under the recorded evaluation conditions.

A PASS does **not** mean:

- the agent is generally safe;
- the model is clinically valid;
- the behavior will generalize to unseen populations;
- the system is ready for production;
- all relevant failure modes were evaluated;
- an organization should release the system.

## 4. What a FAIL means

A V1.5 `FAIL` means:

> At least one explicitly defined, mechanically evaluable behavioral obligation or invariant was violated under the recorded conditions.

A FAIL identifies a failure in the evaluated pair. It does not establish:

- prevalence of the failure;
- expected production frequency;
- patient harm;
- clinical severity;
- organizational release disposition.

## 5. What REVIEW means

`REVIEW` means:

> The available valid specification or evaluation evidence does not justify a deterministic PASS or FAIL.

For the deterministic V1.5 proof, the canonical offline REVIEW path is specification inconsistency.

REVIEW is not PASS and must never be silently converted into PASS.

## 6. Mechanism proof, not sufficiency proof

V1.5 asks:

> Can this evaluation primitive work correctly on designed cases?

It does not establish:

> Is this evaluation primitive sufficient for real-world evaluation?

Accordingly:

```text
primitive proven
≠
primitive sufficient
```

Even a fully Proven + Done V1.5 leaves broader validity questions open.

## 7. Small-suite limitation

V1.5 targets only 8–12 distinct CasePair specifications across four scenario families.

For an individual safety-critical construct, the suite may contain only a handful of positive instances—on the order of roughly 3–5. As an **illustrative order-of-magnitude comparison, not a V1.5 power calculation**, a powered bound on a rare-event false-negative rate can require on the order of ~140 positive examples depending on the target bound and confidence level.

The point is categorical: V1.5 demonstrates the workflow and mechanism; it does not provide a powered estimate.

The corpus therefore does not support claims about:

- failure prevalence;
- expected model reliability;
- confidence intervals;
- population accuracy;
- comprehensive behavioral coverage.

## 8. No coverage claim

The four scenario families are deliberately selective. They demonstrate that the primitive applies across different behavioral relationships.

They do not establish that the benchmark covers:

- all meaningful agent failures;
- all tool-use failures;
- all multi-turn failures;
- all uncertainty failures;
- all relevant deployment contexts.

Passing every V1.5 pair does not imply that unrepresented failures are absent.

## 9. Synthetic-data limitation

V1.5 uses synthetic fixtures because controlled pairs require explicit knowledge of:

```text
what changed
what remained fixed
what should change
what should remain invariant
```

That improves experimental control. It does not establish that the fixtures represent:

- real patients or users;
- real conversations;
- production workload distributions;
- actual failure prevalence;
- real-world outcome consequences.

Synthetic controllability is not external validity.

## 10. Deterministic reference-agent limitation

The reference agent is intentionally artificial. Its behavior modes create known success and failure conditions.

> Detecting a seeded reference-agent failure proves the evaluator can detect that defined failure.

It does **not** show:

- that production models exhibit the failure;
- how often such failures occur;
- how difficult they are to detect in stochastic models;
- that the same evaluator will generalize without modification.

The reference agent validates evaluator mechanics, not real-model prevalence.

## 11. Controlled-pair limitation

V1.5 ordinarily changes one primary controlled variable. This improves interpretability.

Production systems may change several things simultaneously, including model, prompt, retrieval, memory, tools, permissions, policy, orchestration, and runtime.

V1.5 does not provide general multivariable causal attribution for such changes.

## 12. Deterministic-construct limitation

V1.5 deliberately rejects benchmark cases that can only be evaluated through an unvalidated semantic judge.

That keeps the MVP evidence mechanically inspectable, but it also excludes many important ambiguous behaviors. The deterministic corpus is therefore narrower than the eventual problem domain by design.

## 13. Semantic-judge limitation

Semantic evaluation is deferred.

No V1.5 result establishes that a future automated judge is sufficiently sensitive, specific, calibrated, unbiased, stable across judge models, or an acceptable substitute for human adjudication.

A future semantic judge remains evidence, not ground truth.

## 14. Human-adjudication limitation

V1.5 contains no validated clinician- or expert-rater workflow.

It therefore does not establish:

- inter-rater reliability;
- expert consensus;
- clinically acceptable decision thresholds;
- human validation of ambiguous constructs.

This is the material boundary between the deterministic mechanism proof and later real-world evaluation.

## 15. No statistical inference

See `docs/MVP_SCOPE.md §9` for the canonical non-metrics list.

V1.5 reports proof-obligation outcomes, not population estimators. Designed PASS/FAIL examples must not be reinterpreted as a model accuracy or reliability rate.

## 16. No clinical-validity claim

See `docs/MVP_SCOPE.md §14` for the canonical claims ceiling.

The repository does not establish that the encoded obligations are clinically correct for real deployment, nor does it establish clinical efficacy or patient safety.

## 17. No regulatory or production-readiness claim

TRACE-Well produces engineering evaluation evidence. It does not establish regulatory compliance, authorization, or sufficiency for a regulatory submission.

V1.5 also intentionally omits production-system concerns such as enterprise IAM, high availability, production databases, operational monitoring, incident response, approval workflows, residual-risk management, and live clinical connectivity.

Passing V1.5 does not establish production readiness.

## 18. Observable-evidence limitation

TRACE-Well evaluates observable traces and does not capture hidden chain-of-thought.

It can establish what was observed, what action occurred, what tool was used, and what authorization state applied. It does not claim to recover the system's true internal causal reasoning.

A generated rationale remains generated output, not privileged provenance.

## 19. Reproducibility limitation

V1.5's strongest reproducibility claim applies to deterministic built-in execution.

Equivalent reproduction requires the same effective artifact plus recorded execution configuration, including execution source, agent identity/version, `agent_mode`, tool-policy version, evaluator versions, and code/runtime identity.

A matching `artifact_digest` alone does not prove execution or verdict reproduction.

## 20. Imported-trace limitation

TRACE-Well can reproducibly reevaluate persisted external traces.

That does not mean TRACE-Well can reproduce the external runtime that originally generated them.

```text
re-evaluation reproducibility
≠
upstream execution reproducibility
```

## 21. Mitigation-verification limitation

Mitigation verification reruns both sides of the same controlled CasePair.

A successful verification establishes only that the explicit closure criterion held for that pair under the recorded conditions.

It does not establish that the mitigation works across unseen cases, eliminates related failures, or introduced no other regression outside the evaluated pair.

## 22. Holdout limitation

The holdout tests a narrow engineering property: whether the system can process a valid pair not used in ordinary development execution.

It does not establish statistical generalization, external validity, or unseen-population robustness.

## 23. REVIEW limitation

REVIEW protects against manufacturing certainty. It does not solve ambiguity.

A REVIEW result means the available valid specification/evidence cannot support deterministic PASS or FAIL under the defined rules. The existence of REVIEW is a discipline mechanism, not evidence that the unresolved case has been correctly adjudicated.

## 24. External-trace visibility limitation

Imported traces expose only the evidence supplied by the external system. TRACE-Well may lack visibility into hidden upstream configuration, provider-side changes, routing behavior, environment-specific settings, or unrecorded upstream state.

Missing upstream provenance must remain missing. Do not infer it.

## 25. Public-text scanner limitation

The generic repository scanner catches structural/contextual patterns. It cannot determine the private significance of every arbitrary proper noun.

> **A passing generic scan does not prove that every sensitive organization, person, model, product, or other private identifier is absent.**

Where private development materials were used, publication additionally requires local sensitive-term augmentation and maintainer review.

## 26. Public-neutrality tradeoff

The public repository intentionally omits private context that is kept out of tracked files.

That improves portability and public neutrality. Those omitted private rationales must not be reconstructed into tracked files.

## 27. Minimal-dependency tradeoff

V1.5 deliberately avoids a general evaluation framework as its controlling abstraction.

Benefits include a small dependency surface, an inspectable evaluation primitive, and credential-free deterministic execution. The cost is that some commodity plumbing is implemented locally and broader integrations are deferred.

This is an accepted engineering tradeoff, not evidence that bespoke infrastructure is universally superior.

## 28. File-based persistence tradeoff

File-based evidence is simple to inspect and reproduce, but it does not provide operational-scale querying, multi-user concurrency, database transactions, or enterprise evidence management.

Those are outside V1.5.

## 29. Proven versus Done versus Sufficient

The PRD requires:

```text
Proven
AND
Done
```

A green build can still fail the product proof. Likewise, satisfying the proof obligations does not establish broader sufficiency.

```text
Done ≠ Proven
Proven ≠ Sufficient
```

All three states matter.

## 30. Appropriate public summary

Appropriate:

> **TRACE-Well V1.5 demonstrates a reproducible paired behavioral-evaluation mechanism on controlled synthetic cases.**

Appropriate:

> **Its deterministic reference suite demonstrates evaluator mechanics, including required changes, invariant preservation/violation, REVIEW behavior, and paired mitigation verification.**

Appropriate:

> **The resulting evidence can serve as one bounded input to a broader evaluation or governance process; it is not a substitute for validated human judgment, statistical validation, or organizational decision authority.**

## 31. Unsupported claims

Do not describe V1.5 as clinically proven, safe AI, validated medical AI, regulatory compliant, guaranteeing safety, production ready, or a comprehensive safety evaluation.

Use the exact canonical claims boundary in `docs/MVP_SCOPE.md §14` rather than expanding this list elsewhere.

## 32. Reviewer interpretation questions

Before drawing a conclusion from a V1.5 result, ask:

1. What exact CasePair was evaluated?
2. What behavior was required to change?
3. What behavior was required to remain invariant?
4. What observable evidence supports the verdict?
5. Was the run built-in or imported, and what execution configuration applied?
6. Can the result be reproduced from persisted evidence?
7. **What does this result not support?**

If the final answer is unclear, the interpretation is too broad.

## 33. Final limitation statement

> **TRACE-Well V1.5 is a deliberately narrow deterministic mechanism proof. Its strongest unresolved limitation is that the semantic and human-adjudication layers needed for ambiguous real-world evaluation have not yet been validated. The current evidence therefore supports reproducible engineering conclusions only within the explicitly designed synthetic cases, constructs, execution conditions, and claims boundary of the repository.**
