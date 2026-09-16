# TRACE-Well V1.5 — Independent Reproduction Runbook

This procedure is the human/operator portion of PO-9. Automated CI cannot establish that an independent person reproduced the result without author knowledge.

## Purpose

Demonstrate that a third party can obtain a clean checkout, install the documented environment, execute the deterministic harness, and reproduce the expected conclusion using only tracked public repository information.

The load-bearing claim is not merely that “someone else ran the code.” It is that an eligible independent operator can reproduce the result **from public documentation alone, without author clarification or unstored tribal knowledge**.

## Independent operator eligibility

The operator used for final PO-9 signoff should:

- not be the original author;
- have had no prior exposure to TRACE-Well design discussions, private planning notes, unpublished implementation guidance, or author walkthroughs;
- not have participated in developing, debugging, reviewing, or preparing the V1.5 implementation or reproduction procedure;
- receive only the public repository location and the tracked instructions in this runbook;
- perform the reproduction from a clean checkout and environment.

Prior familiarity with general Python, Git, CI, or evaluation-engineering concepts is acceptable. Prior knowledge of TRACE-Well-specific intent or undocumented conventions is not.

If no sufficiently unexposed operator is available, PO-9 independent-human signoff remains pending. Do not weaken the eligibility standard merely to close the release gate.

## No-side-channel rule

During the signoff attempt, the operator must not receive author clarification, private messages, live walkthroughs, unpublished commands, or other TRACE-Well-specific assistance beyond tracked public repository material.

Ordinary interpretation of standard tooling documentation is allowed. TRACE-Well-specific clarification from the author or another informed project participant is not.

## Clarification / failure protocol

If the operator cannot proceed using the public repository alone, or asks for TRACE-Well-specific clarification:

1. **Stop the signoff attempt.** Do not answer the question through a private side channel and continue the same attempt.
2. Record the blocking point as a **documentation or repository-sufficiency defect**, not as an operator failure.
3. Fix the defect in tracked public documentation, code, CLI behavior, or repository structure as appropriate.
4. Run the ordinary CI and automated clean-runner reproduction gates against the corrected commit.
5. Restart the reproduction from a clean checkout of the corrected commit.
6. Prefer a fresh eligible operator. If the same operator is reused, treat the earlier exposure as contamination and do not describe the rerun as blind unless the information they received was limited strictly to the now-public corrected material and the acceptance record makes that limitation explicit.

A successful signoff must therefore be against **public repository material alone**, not public material plus an undocumented conversation.

## Preconditions

Use a machine or clean environment that does not rely on:

- the original author's virtual environment;
- unstored shell aliases or environment variables;
- private local notes;
- `.private/sensitive_terms.txt`;
- model credentials;
- network inference services.

Internet access may be used only to obtain the public repository, Python packages required by `pyproject.toml`, and ordinary public documentation for standard tools when needed.

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

The independent operator should complete and retain the following record in their own words:

```text
Repository commit:
Operator identifier or role:
Execution date:
Python version:
Platform:
Prior TRACE-Well design exposure: none / describe
Author or project-member clarification used: no / yes (if yes, attempt is not valid for signoff)
pytest result:
public-text scan result:
PASS reproduction result:
FAIL reproduction result:
REVIEW reproduction result:
artifact digest match across mode-only change:
holdout result:
unexpected deviations:
documentation defects encountered:
```

The operator must also include the following **first-person self-attestation** (or substantively equivalent wording):

> I attest that I performed this reproduction from a clean checkout using only the public TRACE-Well repository and ordinary public documentation for standard tools. Before this attempt, I had no prior exposure to TRACE-Well design discussions, private planning, unpublished guidance, implementation/review work, or preparation of this reproduction procedure. I did not receive TRACE-Well-specific clarification, walkthroughs, or side-channel assistance from the author or another informed project participant during the attempt. The results recorded above are my own observations from this execution.

The self-attestation must be authored or affirmatively adopted by the operator. The original author or project maintainer must not attest to operator eligibility on the operator's behalf.

If any attestation statement is false, uncertain, or requires qualification, record that qualification explicitly and treat the attempt as **not sufficient for blind PO-9 signoff** until the acceptance criteria are met.

Do not record private or sensitive personal information in the public repository unless intentionally approved for publication. The attestation can use a role, initials, or other non-sensitive operator identifier if public disclosure of identity is unnecessary.

## PO-9 closure rule

PO-9 independent reproduction is complete only when an **eligible independent operator with no prior TRACE-Well design exposure** executes this runbook from a clean checkout, records a successful result **using public repository documentation alone, without author or informed-project-member clarification**, and personally provides the required eligibility/no-side-channel self-attestation.

If clarification was required, that attempt is evidence of a documentation/repository-sufficiency defect and is not a valid signoff. Correct the public material and repeat the procedure under the failure protocol above.

The existence of this runbook, a passing automated clean-runner report, and green CI are necessary support, but are not themselves independent-operator signoff.
