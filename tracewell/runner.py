"""Deterministic pair execution orchestration and run manifests.

See docs/ARCHITECTURE.md §§20–23 and docs/REPRODUCIBILITY.md.
"""

from __future__ import annotations

from datetime import datetime, timezone
import platform
import subprocess

from .canonical import CANONICALIZATION_VERSION, artifact_digest
from .comparator import compare_pair, required_constructs
from .evaluator import EVALUATOR_ID, evaluate_case
from .external import evaluate_external_pair
from .models import BehaviorDeltaResult, CasePair, RunManifest, Trace
from .reference_agent import AgentMode, ReferenceAgent


def run_pair(
    pair: CasePair,
    *,
    run_id: str,
    agent: ReferenceAgent,
    mode: AgentMode,
) -> tuple[Trace, Trace, BehaviorDeltaResult, RunManifest]:
    """Execute both conditions and evaluate them through the single comparator path."""
    constructs = required_constructs(pair)
    canonical_trace = agent.run(pair.canonical_case, run_id=f"{run_id}:canonical", mode=mode)
    perturbed_trace = agent.run(pair.perturbed_case, run_id=f"{run_id}:perturbed", mode=mode)
    canonical_results = evaluate_case(pair.canonical_case, canonical_trace, constructs)
    perturbed_results = evaluate_case(pair.perturbed_case, perturbed_trace, constructs)
    result = compare_pair(pair, canonical_results, perturbed_results)
    manifest = _manifest(
        pair,
        run_id=run_id,
        execution_source="agent_runner",
        agent=agent,
        agent_mode=mode,
    )
    return canonical_trace, perturbed_trace, result, manifest


def evaluate_imported_pair(
    pair: CasePair,
    *,
    run_id: str,
    canonical_trace: Trace,
    perturbed_trace: Trace,
) -> tuple[BehaviorDeltaResult, RunManifest]:
    """Evaluate fixed external evidence and record trace-source provenance."""
    result = evaluate_external_pair(pair, canonical_trace, perturbed_trace)
    manifest = _manifest(
        pair,
        run_id=run_id,
        execution_source="trace_source",
        agent=None,
        agent_mode=None,
    )
    return result, manifest


def _manifest(
    pair: CasePair,
    *,
    run_id: str,
    execution_source: str,
    agent: ReferenceAgent | None,
    agent_mode: str | None,
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        case_pair_id=pair.pair_id,
        case_pair_version=pair.version,
        artifact_digest=artifact_digest(pair),
        canonicalization_version=CANONICALIZATION_VERSION,
        execution_source=execution_source,
        agent_id=agent.agent_id if agent is not None else None,
        agent_version=agent.agent_version if agent is not None else None,
        agent_mode=agent_mode,
        model=None,
        model_version=None,
        prompt_version=None,
        tool_policy_version=None,
        evaluator_versions={"deterministic": EVALUATOR_ID},
        code_sha=_code_sha(),
        runtime_version=platform.python_version(),
    )


def _code_sha() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = proc.stdout.strip()
    return value or None
