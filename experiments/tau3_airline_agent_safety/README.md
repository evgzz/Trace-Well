# TRACE-Well × τ³-bench — Airline Agent Safety

This experiment integrates TRACE-Well's evidence/replay philosophy with the pinned τ³/tau2-bench airline environment.

Pinned upstream τ³ commit: `b7ea9074c1cba482b30687fecdb5c8425fd6f619`.

## Safety question

Can a stochastic tool-using agent preserve explicit authorization, ignore untrusted tool-result instructions, retain a late scope restriction, and recover safely from a consequential tool failure?

## Architecture

```mermaid
flowchart TD
    U[Controlled User Protocol] --> A[Stochastic Agent]
    A --> T[τ³ Airline Tools]
    T --> E[Isolated Environment]
    E --> X[Instrumented Trajectory]
    X --> W[TRACE-Well Adapter]
    W --> O[Behavioral Obligations]
    O --> V[PASS / FAIL / REVIEW]
    V --> F[Finding]
    F --> M[Mitigation]
    M --> R[Unchanged Regression Rerun]
    R --> H[Holdout]
    H --> D[Residual Risk]
    D --> G[GO / NO-GO / INCONCLUSIVE]
```

## Four conditions

- A clean baseline
- B indirect prompt injection in untrusted tool result
- C B + late reservation-scope narrowing
- D C + native-shaped write failure

See `EXPERIMENT_PLAN.md` and `RISK_REGISTER.md`.

## Evidence rule

Environment/tool telemetry is authoritative for execution and mutation. Assistant text is never used to infer that a write succeeded.

Unknown execution evidence remains unknown and yields REVIEW where required.

## Reproduction

The repository CI tests the adapter/evaluator without τ³ installed.

Live execution additionally requires:
1. a checkout of pinned tau2-bench;
2. installation of its dependencies;
3. a supported model/provider credential;
4. passing gates G0–G7.

No live-model result should be committed or claimed until those gates pass.
