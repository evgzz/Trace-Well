# TRACE-Well: Longitudinal and Multi-Turn AI Safety Evaluation

**EG14Y AI Evaluation & Assurance Whitepaper Series — Paper 08 of 10**
**Version:** 1.0
**Date:** 2026-09-16
**Primary home:** TRACE-Well

> **Claim boundary.** TRACE-Well V1.5 is a mechanism proof on controlled
> synthetic cases. Its public claim ceiling is **prototype engineering
> evaluation evidence**. It is not a model leaderboard, a production safety
> platform, a clinical decision-support system, or a statistical generalization
> study, and V1.5 must not be described as *fully Proven* until an independent
> blind human reproduction and operator self-attestation have actually been
> recorded.

---

## Abstract

Safety is not a property of a single response; it is a property of a
*trajectory*. An agent can answer the first turn perfectly and then, as context
accumulates and user state evolves, quietly drop an escalation, abandon an
abstention, or let a control lapse. TRACE-Well is a small, reproducible,
open-source paired/counterfactual behavioral evaluation harness built to measure
exactly this: whether appropriate behavior, escalation, abstention, and safety
controls **persist** across complete interaction trajectories, and whether a
configured mitigation survives *both* sides of a counterfactual rather than
merely coinciding with a good run.

---

## 1. The gap: isolated responses hide trajectory failures

Most evaluation scores one prompt and one response. But the failures that matter
in a longitudinal, multi-turn deployment are precisely the ones a single-response
test cannot see:

- an escalation that was correct on turn one is **not repeated** when the same
  condition recurs later;
- an abstention (`Unknown`, "I can't verify that") **erodes** as the
  conversation applies pressure;
- a safety control that held under a benign framing **lapses** under an evolved
  user state;
- a fix appears to work only because the run happened to avoid the triggering
  path.

TRACE-Well targets the question underneath all of these: does required behavior
*survive change*?

---

## 2. The core method: paired counterfactuals

TRACE-Well evaluates a **CasePair** — a canonical trace and a perturbed
(counterfactual) trace — rather than a single trajectory. The pair is
authoritative for what should change across conditions and what must stay
invariant. This yields a much stronger signal than a single run:

- an **expected change** confirms the agent *does* adapt when it should (e.g.,
  escalates when the counterfactual introduces the triggering condition);
- an **invariant** confirms the agent does *not* break something that should
  have stayed constant;
- the pair together tests whether a mitigation holds on **both** sides — the
  executable signature of a controlled fix rather than a lucky pass.

Agent modes are execution configuration; they do not create new CasePair
identities, so the unit of comparison stays stable.

---

## 3. Deterministic verdicts: PASS / FAIL / REVIEW

TRACE-Well prefers deterministic checks wherever mechanically possible and
evaluates observable evidence only. Its pipeline produces a pair-level verdict
under explicit precedence:

```text
valid CasePair + canonical Trace + perturbed Trace
→ per-condition deterministic evaluation (×2)
→ specification consistency
→ construct indexing
→ observed changes → expected-change checks → invariant checks
→ pair-verdict precedence
→ PASS / FAIL / REVIEW
```

Three governing choices make the verdicts trustworthy:

1. **Invalid input is rejected *before* a verdict.** Malformed traces,
   schema-invalid pairs, unsupported identity-bearing values, or trace/case
   mismatches never receive a PASS/FAIL/REVIEW — they are rejected outright.
2. **`REVIEW` is reserved for genuinely unresolved evaluation** on otherwise
   valid inputs, not used as a soft failure. It is the harness's version of the
   program-wide INCONCLUSIVE state: an honest "not decidable," never a disguised
   pass.
3. **Every established deterministic failure is preserved.** A `FAIL` persists a
   `finding`; the verdict cannot be silently discarded.

The construct vocabulary is deliberately behavioral and order-aware —
`escalation`, `tool_authority_respected`, `required_tool_invoked`,
`prohibited_tool_invoked`, `required_evidence_present`, and trajectory
obligations such as `revised_after:<marker>` — so that "the escalation persisted
across the trajectory" is a mechanical determination, not an impression.

---

## 4. Evidence you can inspect and reproduce

Every run persists an inspectable evidence bundle:

```text
manifest.json
canonical_trace.json
perturbed_trace.json
result.json
(finding.json on a deterministic FAIL)
```

Reproducibility is treated as a first-class, staged claim. Automated
clean-runner reproduction is implemented (`scripts/reproduce_po9.py`) and writes
a report that *explicitly states it is an automated runner and not an
independent-human signoff*. The final proof gate — a previously unexposed human
operator reproducing the required PASS/FAIL/REVIEW, digest-invariance,
development-suite, and holdout results from public materials alone, with no
side-channel help — remains deliberately open. If that operator needs
TRACE-Well-specific clarification, the attempt is a *documentation-sufficiency
defect*, the public material is fixed, and the attempt restarts from a clean
checkout. This is reproducibility held to an unusually honest standard.

---

## 5. Corpus and controls

The V1.5 corpus is small by design and control-rich: distinct development
CasePairs each with an expected PASS direction and a matched seeded FAIL
direction, a separately executed holdout CasePair, and a dedicated
inconsistent-specification fixture that must resolve to `REVIEW`. The holdout and
the seeded faults are what let the harness demonstrate it can *detect* the
failures it names rather than merely pass safe fixtures — the same test-of-tests
discipline used across the program.

---

## 6. Place in the program

TRACE-Well is the series' instrument for the *longitudinal* dimension of the
lifecycle (Paper 01). Where WellTrace evaluates a configured system's release
readiness and the PA Readiness Agent supplies a real multi-step workflow,
TRACE-Well answers whether safety-relevant behavior holds up *as context and
user state evolve*. Its paired-counterfactual PASS/FAIL/REVIEW findings feed the
same structured attribution (Paper 06) and the same regression loop (Paper 07):
a persistence failure becomes a frozen CasePair that every later configuration
must survive on both sides.

---

## 7. Non-goals

- TRACE-Well is **not** a model leaderboard or a statistical study; it is a
  deterministic mechanism proof.
- It does **not** establish clinical validity, patient safety, or production
  readiness.
- V1.5 is **not** *fully Proven* until the independent blind human reproduction
  and operator self-attestation are recorded.

---

## 8. Conclusion

Trajectory failures are invisible to single-response evaluation and dangerous in
exactly the systems we most want to trust. TRACE-Well makes them visible by
evaluating paired counterfactuals with deterministic, order-aware, PASS / FAIL /
REVIEW verdicts, by preserving every established failure, by reserving an honest
"unresolved" state, and by holding reproducibility to a blind-human standard. It
measures the property that matters most in a longitudinal deployment: whether
doing the right thing *persists*.

---

## References (in-repository)

- `docs/MVP_SCOPE.md` — scope, non-goals, Proven vs Done
- `docs/EVALUATION_SPEC.md` — deterministic comparator and verdict precedence
- `docs/BENCHMARK_DESIGN.md` — CasePair design, controls, holdout
- `docs/REPRODUCIBILITY.md`, `docs/REPRODUCTION_RUNBOOK.md`, `docs/ACCEPTANCE.md`
- `docs/LIMITATIONS.md`

## Related papers in this series

- Paper 01 — The end-to-end evaluation and assurance lifecycle
- Paper 02 — A reusable evaluation architecture for agentic systems
- Paper 06 — Structured failure attribution
- Paper 07 — The continuous mitigation and regression loop
