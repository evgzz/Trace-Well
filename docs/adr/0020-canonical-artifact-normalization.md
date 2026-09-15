# ADR-0020 — Canonical Artifact Normalization

**Status:** Accepted  
**Spec:** `docs/ARCHITECTURE.md`, `docs/REPRODUCIBILITY.md`

## Context

Source YAML/JSON formatting must not define semantic artifact identity, while meaningful specification changes must produce distinct identities.

## Decision

The identity pipeline is:

```text
authored YAML/JSON
→ parse
→ validate
→ resolve effective object
→ canonical JSON serialization
→ SHA-256 artifact_digest
→ execute the exact same effective object
```

`source_digest` may optionally identify exact authored bytes, but it is not semantic identity.

Persist `canonicalization_version`.

Identity-bearing unconstrained binary floats are rejected. Fractional identity values, if needed, require an exact normalized representation such as a decimal string.

Semantically ordered arrays preserve order. Changes to canonical serialization semantics require incrementing `canonicalization_version`.

Free-form non-semantic metadata is excluded from `artifact_digest`. Information that affects evaluation identity must be represented in an explicit identity-bearing field.

## Consequences

- Equivalent authoring formats can share one semantic identity.
- Meaningful changes produce different digests.
- The object that is hashed is the object that is executed.
- Historical digests remain interpretable through canonicalization versioning.

## Alternatives rejected

- Hashing raw YAML/JSON source as semantic identity: rejected because formatting changes would alter identity.
- Executing a separately reconstructed object after hashing: rejected because hash/execution drift would undermine provenance.
- Unconstrained binary floating-point values in identity fields: rejected because representation can be unstable.

---

**Implements:** PO-9  
**Related ADRs:** 0010, 0016
