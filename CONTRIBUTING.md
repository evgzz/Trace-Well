# Contributing to TRACE-Well

TRACE-Well preserves a frozen deterministic V1.5 reference and an integrated-but-empirically-unvalidated V1.6 semantic-judge development path. Contributions should preserve evidence boundaries and keep new experiments distinguishable from established results.

## Before changing code

Read:

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/MVP_SCOPE.md`
4. `docs/PRD.md`
5. `docs/ARCHITECTURE.md`
6. `docs/EVALUATION_SPEC.md`
7. `docs/BENCHMARK_DESIGN.md`
8. `docs/REPRODUCIBILITY.md`
9. `docs/LIMITATIONS.md`

If a proposed change alters a load-bearing decision, add a new Proposed ADR. Do not rewrite the Decision section of an Accepted ADR.

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Required checks

Before submitting a change:

```bash
pytest
python scripts/check_public_text.py
python scripts/demo.py
```

The offline demo must verify PASS/FAIL/REVIEW evidence and does not establish model-level validity.

Both must pass without model credentials or network inference.

## Dependency rule

Base dependencies are constrained by ADR-0016 and `tests/test_dependency_boundary.py`.

Prefer:

1. standard library;
2. an existing approved dependency;
3. a small repository-owned implementation;
4. a new dependency only when the build/buy boundary has been deliberately revisited.

## Benchmark contributions

The frozen V1.5 CasePair inventory must not be silently changed. Add new studies under a separately declared experimental scope rather than altering the frozen V1.5 corpus.

Do not inflate benchmark size by treating reference-agent modes as new CasePairs. Pair identity and run configuration are separate.

## Public repository hygiene

Do not commit private employment, recruiting, interview, application, customer-targeting, prospect-targeting, or private partnership context.

When local private materials are used, maintain an untracked `.private/sensitive_terms.txt` and run the publication scanner before committing.

## Claims discipline

Keep public claims within:

> Prototype engineering evaluation evidence.

See `docs/LIMITATIONS.md` for the interpretation boundary.
