"""TRACE-Well command line entry point.

Only implemented commands are documented here; future CLI surfaces remain deferred.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from .evidence import write_run_evidence
from .external import parse_external_trace
from .lifecycle import create_finding
from .loader import load_case_pair
from .reference_agent import ReferenceAgent
from .runner import evaluate_imported_pair, run_pair

app = typer.Typer(help="TRACE-Well deterministic evaluation harness.")


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo("1.5.0")


@app.command("run-pair")
def run_pair_command(
    pair_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    mode: str = typer.Option(..., "--mode"),
    run_id: str = typer.Option(..., "--run-id"),
    output_dir: Path = typer.Option(Path("results/runs"), "--output-dir"),
) -> None:
    """Run one CasePair with the deterministic reference agent."""
    pair = load_case_pair(pair_path)
    canonical_trace, perturbed_trace, result, manifest = run_pair(
        pair,
        run_id=run_id,
        agent=ReferenceAgent(),
        mode=mode,  # ReferenceAgent validates supported modes.
    )
    finding = create_finding(pair, result)
    run_dir = write_run_evidence(
        output_dir,
        canonical_trace=canonical_trace,
        perturbed_trace=perturbed_trace,
        result=result,
        manifest=manifest,
        finding=finding,
    )
    typer.echo(f"{result.pair_result.value} {run_dir}")


@app.command("evaluate-traces")
def evaluate_traces_command(
    canonical_trace_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    perturbed_trace_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    pair_path: Path = typer.Argument(..., exists=True, dir_okay=False, readable=True),
    run_id: str = typer.Option(..., "--run-id"),
    output_dir: Path = typer.Option(Path("results/runs"), "--output-dir"),
) -> None:
    """Evaluate conforming external traces through the same evaluator/comparator."""
    pair = load_case_pair(pair_path)
    canonical_payload = json.loads(canonical_trace_path.read_text(encoding="utf-8"))
    perturbed_payload = json.loads(perturbed_trace_path.read_text(encoding="utf-8"))
    canonical_trace = parse_external_trace(
        canonical_payload,
        expected_case_id=pair.canonical_case.case_id,
    )
    perturbed_trace = parse_external_trace(
        perturbed_payload,
        expected_case_id=pair.perturbed_case.case_id,
    )
    result, manifest = evaluate_imported_pair(
        pair,
        run_id=run_id,
        canonical_trace=canonical_trace,
        perturbed_trace=perturbed_trace,
    )
    finding = create_finding(pair, result)
    run_dir = write_run_evidence(
        output_dir,
        canonical_trace=canonical_trace,
        perturbed_trace=perturbed_trace,
        result=result,
        manifest=manifest,
        finding=finding,
    )
    typer.echo(f"{result.pair_result.value} {run_dir}")


if __name__ == "__main__":
    app()
