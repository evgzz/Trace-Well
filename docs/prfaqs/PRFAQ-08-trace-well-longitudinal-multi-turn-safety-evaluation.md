# PRFAQ 08 — TRACE-Well: Longitudinal and Multi-Turn AI Safety Evaluation

**EG14Y AI Evaluation & Assurance PRFAQ Series — 8 of 10**
**Format:** Amazon-style working-backwards PRFAQ · **Version:** 1.0 · **Date:** 2026-09-16
**Home repository:** TRACE-Well

> **How to read this document.** Working-backwards PRFAQ; the Press Release uses
> the future, "already-launched" voice by convention. Customer names and quotes
> are **illustrative composite personas** modeled on an enterprise assistant/
> platform buyer and a large health system — not real endorsements. See
> **§ Current status vs. this PRFAQ**.

---

## Customer problem

> "Our assistant is safe on turn one. But over a long conversation — as context
> accumulates and the user's state changes — it quietly stops escalating, drops
> an abstention it made earlier, or lets a safety control lapse. Single-response
> evals never see it, because the failure is in the *trajectory*, not any one
> answer."

- **Platform buyer (Microsoft-like).** A team shipping multi-turn assistants
  needs to know whether safety-relevant behavior *persists* across a whole
  interaction, not just on isolated prompts.
- **Health-system buyer (Mayo-like).** A clinical-AI safety team must verify that
  escalation and abstention hold as a patient's described situation evolves over
  a session.

---

## Press Release

### EG14Y launches TRACE-Well: measure whether safe behavior *persists* across a whole conversation

**A reproducible paired/counterfactual harness that tests whether appropriate behavior, escalation, abstention, and safety controls survive as context and user state evolve — with deterministic PASS / FAIL / REVIEW verdicts.**

*Working-backwards dateline* — EG14Y today released TRACE-Well, a small,
reproducible, open-source behavioral evaluation harness for the failures that
single-response evaluation cannot see: the ones that emerge across a trajectory.

Safety is a property of a trajectory, not a response. TRACE-Well evaluates a
**CasePair** — a canonical trace and a perturbed (counterfactual) trace — rather
than a single run. An *expected change* confirms the agent adapts when it should
(for example, escalating when the counterfactual introduces the triggering
condition); an *invariant* confirms it doesn't break something that should have
stayed constant; and the pair together tests whether a mitigation holds on
**both** sides — the executable signature of a controlled fix rather than a lucky
pass.

Verdicts are deterministic and honest. The harness prefers mechanical checks,
evaluates observable evidence only, and produces a pair-level PASS / FAIL /
REVIEW under explicit precedence. Invalid inputs — malformed traces, schema-
invalid pairs, trace/case mismatches — are rejected *before* a verdict. `REVIEW`
is reserved for genuinely unresolved evaluation, the harness's honest "not
decidable," never a disguised pass. Every established deterministic failure is
preserved as a finding.

Reproducibility is held to an unusually strict standard: automated clean-runner
reproduction is implemented and its report *explicitly states it is not an
independent-human signoff*, and the final proof gate requires a previously
unexposed human operator to reproduce the results from public materials alone,
with no side-channel help.

"Our assistant passed every one-shot safety test and still let an escalation slip
on turn nine," said an illustrative Director of Conversational AI Safety at a
composite platform vendor. "TRACE-Well measures the thing we actually care about
— whether doing the right thing lasts."

---

## Customer FAQ

**Q: What does a CasePair test that a single prompt can't?**
Whether required behavior *survives change* — an escalation repeated when a
condition recurs, an abstention that doesn't erode under pressure, a control that
holds under an evolved user state.

**Q: What is REVIEW?**
An honest "unresolved evaluation" for otherwise-valid inputs — the harness's
version of an INCONCLUSIVE state, never a soft pass. Invalid inputs are rejected
before any verdict.

**Q: How do I trust the results are reproducible?**
Every run persists an inspectable evidence bundle; automated clean-runner
reproduction is implemented and labeled as *not* a human signoff; and the final
gate demands a blind independent-human reproduction from public materials alone.

**Q: Is this a model leaderboard?**
No. It is a deterministic mechanism proof on controlled synthetic cases.

---

## Internal / stakeholder FAQ

**Q: How does it fit the wider program?**
It is the program's instrument for the longitudinal dimension. Its PASS/FAIL/
REVIEW findings feed the same structured attribution (PRFAQ 06) and regression
loop (PRFAQ 07): a persistence failure becomes a frozen CasePair every later
configuration must survive on both sides.

**Q: What would make it fail?**
Describing V1.5 as "fully Proven" before the blind independent-human reproduction
and operator self-attestation are recorded.

---

## Current status vs. this PRFAQ

Future-voice Press Release; **current reality:** TRACE-Well V1.5 is a mechanism
proof on controlled synthetic cases; the public claim ceiling is *prototype
engineering evaluation evidence*. It is not a model leaderboard, production safety
platform, clinical decision-support system, or statistical study. V1.5 must
**not** be described as fully Proven until the independent blind human
reproduction and operator self-attestation are recorded.

## References

- Companion whitepaper: `docs/whitepapers/WP-08-trace-well-longitudinal-multi-turn-safety-evaluation.md`
- `docs/MVP_SCOPE.md`, `docs/EVALUATION_SPEC.md`, `docs/BENCHMARK_DESIGN.md`, `docs/ACCEPTANCE.md`
