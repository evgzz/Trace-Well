"""TRACE-Well command line entry point.

Only implemented commands are documented here; future CLI surfaces remain deferred.
"""

from __future__ import annotations

import typer

app = typer.Typer(help="TRACE-Well deterministic evaluation harness.")


@app.command()
def version() -> None:
    """Print the package version."""
    typer.echo("1.5.0")


if __name__ == "__main__":
    app()
