# Inspect AI interoperability: metadata-only export

This experiment tests **data-structure interoperability**, not evaluation equivalence.

Inspect AI supports JSONL datasets containing `Sample` fields such as `id`, `input`, and `metadata`. TRACE-Well's CasePair is a two-condition evaluation specification containing tool authorization, expected behavior changes, and invariants. Its semantics cannot be reproduced by a single plain-text prompt.

## Export

After `pip install -e '.[dev]'`, run:

```bash
python scripts/export_inspect_samples.py \
  --case cases/dev/auth-001.yaml \
  --output results/runs/inspect-export.jsonl
```

The output has one JSONL row with:

- a stable `id` from the CasePair identity and version;
- a textual `input` explicitly marked **NON-EXECUTABLE**;
- `metadata.tracewell_case_pair` containing the lossless, schema-validated CasePair;
- source-file SHA-256 distinct from TRACE-Well's canonical artifact digest;
- **no `target`**, no solver, no scorer, no scored result.

The script declines to export a `cases/holdout/` file unless `--include-holdout` is explicitly supplied. Exporting a case does not modify the frozen benchmark inventory or reference evaluation.

## Optional Inspect import

Inspect AI is **not** a base dependency. An external experimenter with `inspect_ai` installed may inspect the record using the documented `json_dataset` API:

```python
from inspect_ai.dataset import json_dataset
dataset = json_dataset("results/runs/inspect-export.jsonl")
sample = dataset[0]
print(sample.id)
print(sample.metadata["execution_status"])  # NOT_EXECUTABLE
```

**Do not call `inspect eval` on this record** as though it were a configured TRACE-Well behavioral evaluation. Doing so would test the explanatory input, not an agent's paired tool behavior.

## Requirements for a future executable bridge

An actual Inspect `Task` must independently define and validate:

1. two executions per CasePair with explicit canonical/perturbed context;
2. tool definitions, authorizations, and sandbox/replay policy for each condition;
3. stable trajectory event provenance, including successful downstream effects;
4. a scorer implementing or delegating to TRACE-Well's actual comparator;
5. PASS/FAIL/REVIEW mapping that does **not** collapse REVIEW into success;
6. comparative tests showing agreement with the frozen deterministic cases.

The exporter does **not** satisfy these requirements and has no model-evaluation result. See [Inspect datasets](https://inspect.aisi.org.uk/datasets.html) for the external schema and [TRACE-Well evaluation specification](EVALUATION_SPEC.md) for the authoritative paired semantics.
