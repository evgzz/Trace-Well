# Documentation index

Start with [the project README](../README.md) for the research question, demo, evidence status, and repository map. The files below are deliberately separated by function; a convenience guide does not override the canonical specification or frozen evidence.

## Reproduce or understand a run

| Question | Reference |
|---|---|
| How can I run the three-case offline demo? | [Annotated example](../examples/README.md), [full V1.5 walkthrough](DEMO.md) |
| What exactly is evaluated? | [Evaluation specification](EVALUATION_SPEC.md), [benchmark design](BENCHMARK_DESIGN.md) |
| How are evidence and artifacts defined? | [Architecture](ARCHITECTURE.md), [reproducibility](REPRODUCIBILITY.md) |
| What do results **not** establish? | [Limitations](LIMITATIONS.md) |
| What is completed versus pending? | [V1.5 acceptance](ACCEPTANCE.md), [V1.6 acceptance](V1.6_ACCEPTANCE.md) |

## Interoperability

- [Inspect AI metadata-only export](INSPECT_EXPORT.md) explains the Sample-shape record and why it is not an executable Task or scorer.

## Research responsibility

- [Research boundaries](RESEARCH_BOUNDARIES.md) distinguish evaluator findings from scientific intervention conclusions and independent release authorization.

## Methods, engineering and decisions

- [V1.5 scope](MVP_SCOPE.md), [PRD](PRD.md), and [proof-obligation/ADR map](PO_ADR_MAP.md) specify the frozen deterministic mechanism.
- [Reproduction runbook](REPRODUCTION_RUNBOOK.md) gives the independent-human protocol; the automated CI runner is insufficient for that signoff.
- [V1.6 scope](V1.6_SCOPE.md), [evaluation plan](V1.6_EVALUATION_PLAN.md), and [real-model runbook](V1.6_REAL_MODEL_RUNBOOK.md) separate implementation from prospective empirical study.
- [ADR registry](adr/README.md) records accepted and proposed decisions; ADR-0015 does **not** authorize semantic-only FAIL.
- [Engineering context](ENGINEERING_CONTEXT.md) records branch/PR handoffs and must be verified against live repository state.
- [Relation to evaluation practice](RELATION_TO_PRACTICE.md), [roadmap](ROADMAP.md) and [change log](../CHANGELOG.md) provide background, not additional safety claims.

## Working rule

Do not equate synthetic evaluator-correctness tests with empirical AI safety effectiveness. Cite the specific frozen case/trace/manifests and state their claims ceiling. Never move a scientific conclusion or release authorization into TRACE-Well solely because a stored result is `PASS`.
