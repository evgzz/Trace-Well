# ADR-0018 — CI and Publication Gating

**Status:** Accepted  
**Spec:** `AGENTS.md`, `.github/workflows/ci.yml`

## Context

Public neutrality and deterministic acceptance must hold in a fresh clone. Local hooks or private files alone cannot be authoritative.

## Decision

Tracked CI must run, at minimum:

```text
pytest
python scripts/check_public_text.py
```

The base CI path requires no model credentials, private term files, or network inference.

Local pre-commit checks are recommended but are not the sole gate.

When private development materials were used, publication readiness consists of:

1. generic tracked CI scan;
2. optional untracked `.private/sensitive_terms.txt` augmentation;
3. maintainer publication review.

The generic scanner must remain provider-neutral and must not embed private proper nouns.

## Consequences

- Fresh-clone CI is independently useful.
- Private term lists do not leak into the public repository.
- A green generic scan is explicitly not proof that every arbitrary sensitive proper noun is absent.

## Alternatives rejected

- Local-only scanning: rejected because it cannot protect public contributions or CI.
- Public denylist containing private names: rejected because the control would itself disclose the information it is meant to protect.

---

**Implements:** PO-11  
**Related ADRs:** 0012, 0016
