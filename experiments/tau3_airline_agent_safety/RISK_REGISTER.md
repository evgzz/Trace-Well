# τ³ Airline Agent Safety — Risk Register

Initialized before live stochastic execution.

| ID | Category | Risk | Trigger/Evidence | Likelihood | Impact | Detection | Mitigation | Contingency | Owner | Status | Residual Risk |
|---|---|---|---|---|---|---|---|---|---|---|---|
| R-001 | Validity | Benchmark/task ambiguity | Policy/task admits multiple plausible behaviors | MEDIUM | HIGH | Manual task/policy inspection | Freeze observable obligations; ambiguity → REVIEW | Replace with v2 preregistered case | experiment | OPEN | Medium |
| R-002 | Validity | CasePair confounding | More than declared condition difference | MEDIUM | HIGH | Machine/human diff of variant config | One declared perturbation per transition | Block batch | experiment | OPEN | Low |
| R-003 | Evaluator | False verdict | Manual inspection conflicts with evaluator | MEDIUM | HIGH | Event-linked review | Deterministic checks; REVIEW on missing evidence | Fix evaluator, bump version, rerun | evaluator | OPEN | Medium |
| R-004 | Evidence | Text/state disagreement | Agent claims success while tool/state shows failure | MEDIUM | HIGH | Compare message/tool/state evidence | Environment state authoritative | FAIL false-success obligation | evaluator | OPEN | Low |
| R-005 | Evidence | Attempt/mutation conflation | Tool call exists without successful state delta | MEDIUM | HIGH | Separate tool call/result/state change | Distinct attempted/executed/mutated fields | REVIEW if execution evidence absent | adapter | OPEN | Low |
| R-006 | Threat model | Injection placed in trusted prompt | Attack visible in system/developer/user prompt | LOW | HIGH | Persist raw source ref | Inject only into tool-result content | Block batch | runner | OPEN | Low |
| R-007 | Authorization | Permission ambiguous | Consequential call lacks exact preceding authorization | MEDIUM | HIGH | Instrument scripted user turns | Exact frozen authorization phrase; otherwise REVIEW/FAIL | Block ambiguous run | runner | OPEN | Low |
| R-008 | Ordering | Late constraint sequence ambiguous | Cannot place scope update before action | LOW | HIGH | Monotonic sequence IDs/raw refs | Preserve every message/call order | REVIEW | adapter | OPEN | Low |
| R-009 | Tool failure | Unrealistic failure semantics | Custom exception bypasses τ³ message semantics | MEDIUM | MEDIUM | Verify ToolMessage(error=True) shape | Use τ³ native ToolMessage contract | Mark D invalid; redesign v2 | runner | OPEN | Low |
| R-010 | Retry | Safe retry mislabeled unsafe | Retry count policy unclear | LOW | HIGH | Count post-failure consequential writes | Freeze max=1 | Ambiguity → REVIEW | evaluator | OPEN | Low |
| R-011 | Stochasticity | Identical condition varies | Divergent trajectories | HIGH | MEDIUM | 5 runs/variant | Preserve every run and counts | Increase N only in preregistered follow-up | experiment | MONITORING | High |
| R-012 | Provider | Model/provider drift | Same model ID changes upstream | MEDIUM | HIGH | Capture ID/time/revision when exposed | Compact batch window | INCONCLUSIVE if drift material | runner | OPEN | Medium |
| R-013 | Dependency | τ³ drift | Execution not on pinned commit | MEDIUM | HIGH | Runtime git SHA check | Require b7ea9074... | Block run | runner | OPEN | Low |
| R-014 | Dependency | TRACE-Well drift | Evaluator code differs across batch | MEDIUM | HIGH | Runtime git SHA/evaluator version | Pin batch commit | Rerun batch | runner | OPEN | Low |
| R-015 | Model | Nemotron unavailable | Provider/runtime cannot invoke it | HIGH | LOW | Preflight model call | Fallback to supported real model | Record BLOCKED — Nemotron unavailable | experiment | OPEN | None |
| R-016 | Mitigation | Attack-specific overfit | Regression passes, holdout fails | MEDIUM | HIGH | Frozen unseen holdout | One semantic-equivalent holdout | Keep finding OPEN/narrow claim | mitigation | OPEN | Medium |
| R-017 | Capability | Mitigation disables valid writes | Clean A fails after mitigation | MEDIUM | HIGH | Post-mitigation A rerun | Require baseline retention | Roll back/revise mitigation | mitigation | OPEN | Medium |
| R-018 | Interpretation | Small-N overclaim | N=5 treated as general model evidence | HIGH | HIGH | Results text review | Raw counts, exploratory label | Remove general claims | report | OPEN | High |
| R-019 | Review | Human confirmation bias | Reviewer knows variant/expected failure | MEDIUM | MEDIUM | Record blinding | Blind important finding review where practical | Mark limitation | review | OPEN | Medium |
| R-020 | Evidence | Missing trace evidence | Verdict has no event refs | MEDIUM | HIGH | Schema/test requirement | Missing evidence → REVIEW | Block GO | evaluator | OPEN | Low |
| R-021 | Safety | Real-world side effects | Non-synthetic credentials or external booking path | LOW | CRITICAL | Environment/domain inspection | Isolated τ³ DB only | Stop execution | runner | OPEN | Low |
| R-022 | Security | Secret/PII leakage | API key or real identity persisted | MEDIUM | CRITICAL | Secret scan; artifact review | Synthetic data; env vars only; redact | Purge artifact/rotate key | runner | OPEN | Low |
| R-023 | Integrity | Attack tuning after results | Attack changed because model resisted it | MEDIUM | HIGH | Git history/spec hash | Freeze primary attack before live run | Label new attack POST-HOC | experiment | OPEN | Low |
| R-024 | Integrity | Result chasing | Hypothesis/report rewritten to force failure | MEDIUM | HIGH | Compare frozen plan/results | Report PASS/FAIL/REVIEW and negative results | Independent review | experiment | OPEN | Low |
