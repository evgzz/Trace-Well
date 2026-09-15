from pathlib import Path
import re
import tomllib


ALLOWED_RUNTIME_PACKAGES = {
    "pydantic",
    "pyyaml",
    "typer",
    "rich",
}


def _load_pyproject() -> dict:
    path = Path(__file__).parents[1] / "pyproject.toml"
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _distribution_name(requirement: str) -> str:
    """Extract the normalized distribution name from a simple PEP 508 requirement."""
    base = requirement.split(";", 1)[0].strip()
    base = base.split("[", 1)[0]
    match = re.match(r"^[A-Za-z0-9_.-]+", base)
    if not match:
        raise AssertionError(f"Cannot parse dependency requirement: {requirement!r}")
    return match.group(0).lower().replace("_", "-")


def test_base_dependency_ceiling() -> None:
    config = _load_pyproject()
    dependencies = config["project"].get("dependencies", [])
    actual = {_distribution_name(dep) for dep in dependencies}

    unexpected = actual - ALLOWED_RUNTIME_PACKAGES
    assert not unexpected, (
        "Base dependency boundary changed. See ADR-0016 before adding runtime "
        f"dependencies. Unexpected: {sorted(unexpected)}"
    )


def test_pytest_is_dev_only() -> None:
    config = _load_pyproject()
    runtime = {
        _distribution_name(dep)
        for dep in config["project"].get("dependencies", [])
    }
    dev = {
        _distribution_name(dep)
        for dep in config["project"]
        .get("optional-dependencies", {})
        .get("dev", [])
    }

    assert "pytest" not in runtime
    assert "pytest" in dev
