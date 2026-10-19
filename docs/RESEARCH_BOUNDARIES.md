# Research and authority boundaries

TRACE-Well is an **evaluation engine**, not a scientific-results repository, runtime access-control system, or release-authorization service. Its verdict and evidence contracts must not be promoted beyond their demonstrated authority.

| Component | Responsibility | Does not claim |
|---|---|---|
| **TRACE-Well** | Execute defined evaluations; record observed trajectories, deterministic PASS/FAIL/REVIEW and separately qualified semantic evidence | Causal effectiveness, general model safety, production release authorization |
| **SEIL (proposed research program)** | Own hypotheses, preregistration, study analysis, independent adjudication, scientific interpretation and publication | Automatically turn stored evaluator PASS into proof of safety |
| **TRACE-Control (proposed SEIL study)** | Compare control interventions against baseline, assessing whether prohibited downstream effects occur | Duplicate TRACE-Well's evaluator or become a runtime guardrail |
| **WellTrace (separate scoped assurance system)** | Independently qualify imported evidence for a separately defined release decision | Infer causal effects or adopt evaluation verdicts without qualification |
| **Benchmark Commons (separate standards system)** | Deterministic interoperability, FHIR/API/IG version regression and optional vetted fixture distribution | General agent-behavior evaluation |

The above division identifies **intended architectural responsibilities**, not evidence that every proposed system is implemented or integrated. A TRACE-Control experiment may consume TRACE-Well outputs only when the study fixes interventions, controls, independent outcome measures and analysis rules in advance.

## Nonpromotion rule

```text
TRACE-Well observed evidence -> optional SEIL / TRACE-Control scientific analysis
TRACE-Well / research evidence -> optional separate WellTrace qualification
```

A deterministic PASS is scoped to the tested paired specification. It is not a positive claim about unrelated attacks or future model behavior. A semantic-only FAIL stays REVIEW while [ADR-0015](adr/0015-semantic-fail-propagation-vs-review.md) is Proposed and cannot create a SafetyFinding.

## Evidence status

- V1.5: engineering complete on controlled synthetic cases; blind independent-human reproduction pending.
- V1.6: semantic judge protocol, adapters and calibration infrastructure present; real-model empirical validation pending.
- Separate τ³ research branches: do not describe unmerged code or blocked live runs as demonstrated findings.

The [documentation index](README.md), [V1.5 acceptance](ACCEPTANCE.md), [V1.6 acceptance](V1.6_ACCEPTANCE.md), and [limitations](LIMITATIONS.md) control implementation and claim details.
