# ADR-0016 — Build/Buy Boundary: Build the Evaluation Primitive, Buy Commodity Infrastructure

**Status:** Accepted  
**Spec:** `docs/ARCHITECTURE.md`

## Context

TRACE-Well needs a small, inspectable evaluation kernel without adopting a framework that imposes a competing evaluation abstraction or large dependency surface.

## Decision

Use Python >=3.11.

Build repository-owned domain semantics for:

- CasePair/expectation semantics;
- deterministic construct evaluation;
- BehaviorDeltaComparator;
- invariant checking;
- deterministic reference agent;
- trace conformance;
- canonicalization and hashing;
- run provenance;
- findings and paired verification.

Buy commodity infrastructure through a deliberately small base dependency set:

- `pydantic` v2;
- `PyYAML`;
- `typer`;
- `rich`;
- `pytest` as development/test dependency.

Use capability vocabulary rather than provider-centric adapters:

- `case_loader`
- `agent_runner`
- `trace_source`
- `semantic_judge`

External conforming traces are a first-class input path and must converge on the same evaluator/comparator as built-in execution. Missing trace events are never guessed.

Prefer, in order: standard library → approved existing dependency → small repository implementation → new dependency only after explicit architectural justification.

## Consequences

- The evaluation primitive remains legible and under repository control.
- External runtimes are supported without redefining evaluation semantics.
- Heavy inference dependencies stay outside the V1.5 base environment.
- UI and broad framework integration remain deferred by default.

## Alternatives rejected

- General evaluation framework as core abstraction: rejected because lifecycle/dependency weight and competing semantics are not required for V1.5.
- Framework utilities without adopting the framework abstraction: rejected because the dependency/lifecycle cost remains disproportionate for the deterministic core.
- Provider-specific adapter taxonomy: rejected in favor of capability-based seams.

---

**Implements:** PO-10  
**Related ADRs:** 0003, 0004, 0017, 0020
