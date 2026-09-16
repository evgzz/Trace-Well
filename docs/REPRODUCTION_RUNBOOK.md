# TRACE-Well V1.5 — Independent Reproduction Runbook

This procedure is the human/operator portion of PO-9. Automated CI cannot establish that an independent person reproduced the result without author knowledge.

## Purpose

Demonstrate that a third party can obtain a clean checkout, install the documented environment, execute the deterministic harness, and reproduce the expected conclusion using only tracked repository information.

## Preconditions

Use a machine or clean environment that does not rely on:

- the original author's virtual environment;
- unstored shell aliases or environment variables;
- private local notes;
- `.private/sensitive_terms.txt`;
- model credentials;
- network inference services.

Internet access may be used only to obtain the public repository and Python packages required by `pyproject.toml`.

## Procedure

### 1. Obtain a clean checkout

```bash
git clone <public-repository-url> trace-well-repro
cd trace-well-repro
```

Record:

```bash
git rev-parse HEAD
```

### 2. Create the documented environment

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

### 3. Run repository gates

```bash
pytest
python scripts/check_public_text.py
```

Expected: both exit successfully.

### 4. Reproduce a deterministic PASS

```bash
tracewell run-pair \
  cases/dev/auth-001.yaml \
  --mode respect_tool_boundary \
  --run-id repro-auth-pass
```

Expected pair verdict:

```text
PASS
```

Inspect the generated `manifest.json` and record:

- `artifact_digest`;
- `canonicalization_version`;
- `execution_source`;
- `agent_id`;
- `agent_version`;
- `agent_mode`;
- evaluator versions;
- code/runtime identity where available.

### 5. Reproduce a deterministic FAIL

```bash
tracewell run-pair \
  cases/dev/auth-001.yaml \
  --mode violate_tool_boundary \
  --run-id repro-auth-fail
```

Expected pair verdict:

```text
FAIL
```

Confirm a `finding.json` artifact is persisted.

### 6. Confirm artifact/run separation

Compare the two manifests.

Expected:

- the CasePair `artifact_digest` is identical;
- `agent_mode` differs;
- execution provenance differs;
- the pair verdict may differ.

This demonstrates that run configuration does not contaminate CasePair identity.

### 7. Reproduce global REVIEW

```bash
tracewell run-pair \
  cases/fixtures/po7-spec-inconsistent.yaml \
  --mode respect_context \
  --run-id repro-po7-review
```

Expected pair verdict:

```text
REVIEW
```

Confirm `result.json` records specification inconsistency and no normal `finding.json` is created for the REVIEW case.

### 8. Run the development suite

```bash
tracewell run-suite --cases-root cases --run-prefix repro-suite
```

Expected committed inventory structure:

```text
9 distinct development CasePairs
18 deterministic executions
9 PASS
9 FAIL
0 REVIEW
```

The dedicated PO-7 fixture is intentionally outside the normal dev suite.

### 9. Run the holdout explicitly

```bash
tracewell run-holdout --cases-root cases --run-prefix repro-holdout
```

Expected:

```text
1 distinct holdout CasePair
PASS
```

### 10. Optional imported-trace re-evaluation

Use persisted conforming traces with:

```bash
tracewell evaluate-traces \
  <canonical-trace.json> \
  <perturbed-trace.json> \
  cases/dev/auth-001.yaml \
  --run-id repro-imported
```

Confirm the imported path uses `execution_source: trace_source` and the same deterministic evaluation semantics.

## Automated clean-runner support

The repository also contains:

```bash
python scripts/reproduce_po9.py
```

On a clean CI runner this executes the deterministic parts of the procedure, verifies PASS/FAIL/REVIEW, digest invariance across a mode-only change, development-suite counts, and holdout behavior, then writes:

```text
results/reproduction/po9-reproduction-report.json
```

This report is machine-generated support for PO-9. It does **not** replace the independent-human/operator signoff below.

## Signoff record

The independent operator should record:

```text
Repository commit:
Operator identifier or role:
Execution date:
Python version:
Platform:
pytest result:
public-text scan result:
PASS reproduction result:
FAIL reproduction result:
REVIEW reproduction result:
artifact digest match across mode-only change:
holdout result:
unexpected deviations:
```

Do not record private or sensitive personal information in the public repository unless intentionally approved for publication.

## PO-9 closure rule

PO-9 independent reproduction is complete only when an operator other than the original author executes this runbook from a clean checkout and records the result.

The existence of this runbook, a passing automated clean-runner report, and green CI are necessary support, but are not themselves independent-operator signoff.
