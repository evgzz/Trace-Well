# AGENTS.md

> Repository-level instructions for coding agents and contributors working on TRACE-Well V1.5.

## Mission

Implement and maintain TRACE-Well V1.5 as a small, reproducible, open-source paired/counterfactual behavioral evaluation harness.

Priority order:

1. correctness;
2. reproducibility;
3. inspectable evidence;
4. minimal scope;
5. deterministic testing;
6. public-repository neutrality.

Do not expand beyond V1.5.

## Product boundary

TRACE-Well V1.5 is a paired/counterfactual behavioral evaluation harness.

It is not a general benchmark, model leaderboard, production safety platform, clinical decision-support system, medical device, release-governance platform, or multi-agent framework.

Future functionality belongs in `docs/ROADMAP.md` unless an interface must remain extensible.

## Canonical documentation ownership

- `docs/MVP_SCOPE.md` — what V1.5 deliberately does and does not attempt.
- `docs/PRD.md` — what V1.5 must prove.
- `docs/PO_ADR_MAP.md` — which Accepted ADRs enable each proof obligation.
- `docs/adr/` — why load-bearing decisions were made.
- `docs/ARCHITECTURE.md` — canonical domain objects, interfaces, and manifest schema.
- `docs/EVALUATION_SPEC.md` — comparator algorithm and verdict precedence.
- `docs/BENCHMARK_DESIGN.md` — CasePair/fixture design.
- `docs/REPRODUCIBILITY.md` — PO-9 reproduction requirements.
- `docs/LIMITATIONS.md` — claims and interpretation boundary.

Do not redefine a canonical schema in a non-owning document. Link instead.

## ADR rule

When making a load-bearing choice not covered by an existing ADR, create a new `Proposed` ADR before implementation.

Never modify the Decision section of an Accepted ADR. Supersede it with a new ADR.

Mechanical and readily reversible implementation choices do not require ADRs.

## Dependency boundary

Base runtime dependencies are restricted by ADR-0016 and `tests/test_dependency_boundary.py`.

Do not add a base dependency to solve a local implementation problem. Prefer:

1. Python standard library;
2. an existing approved dependency;
3. a small repository-owned domain-specific implementation;
4. a new dependency only after architectural review where the build/buy boundary changes.

Semantic-model or inference dependencies must not enter the base runtime.

## Core semantic rules

- `CasePair.expected_changes` and `CasePair.expected_invariants` are authoritative cross-condition expectations.
- Condition results remain construct-keyed until pair comparison.
- Built-in and external traces converge on the same evaluator/comparator path.
- `REVIEW` never silently becomes `PASS`.
- Global specification inconsistency outranks deterministic behavioral judgment.
- An established deterministic `FAIL` is not erased by unrelated local uncertainty.
- Mitigation verification reruns both members of the CasePair.
- Hidden chain-of-thought is never requested, captured, persisted, or required.
- The deterministic core must run without external model credentials.

## Reference-agent modes

Required deterministic modes include:

- `respect_context`
- `ignore_context`
- `detect_contradiction`
- `ignore_contradiction`
- `respect_tool_boundary`
- `violate_tool_boundary`
- `respect_late_context`
- `ignore_late_context`
- `always_escalate`

The selected mode is run configuration and must be persisted as `agent_mode`. It is not CasePair identity.

## Testing gate

Before considering a change complete, run:

```bash
pytest
python scripts/check_public_text.py
```

Both must pass using the credential-free base environment.

Tests must cover the proof-obligation directions defined by `docs/PRD.md`, including negative controls and failure cases. Green CI over a happy-path-only corpus is not MVP completion.

## Public-text gate

Before every commit, run:

```bash
python scripts/check_public_text.py
```

Do not persist private employment, recruiting, interview, application, customer-targeting, prospect-targeting, or private partnership context in tracked surfaces.

If private development material contains sensitive proper nouns, maintain an untracked:

```text
.private/sensitive_terms.txt
```

with one term or recognizable alias per line.

The built-in scanner must remain useful without that file. Do not hardcode private names into the public scanner.

## Claims discipline

Approved framing:

> Prototype engineering evaluation evidence.

Do not claim that V1.5 establishes clinical validity, clinical efficacy, patient safety, regulatory compliance, comprehensive model safety, statistical generalization, or production readiness.

## Data rules

Synthetic data only. No PHI, live patient records, production clinical data, secrets, or credentials.

## Commands documented in tracked files

Any documented command must exist and run from a clean clone with the documented installation path.

Do not document aspirational commands as implemented behavior.

## Final engineering principle

When design choices conflict, prefer the option that makes evaluation more reproducible, more explicit, easier to inspect, and safer to publish publicly.
