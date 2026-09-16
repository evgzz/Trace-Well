import pytest
from pydantic import ValidationError

from tracewell.models import ExpectedChange, ExpectedInvariant, RunManifest


def test_expected_change_accepts_categorical_transition() -> None:
    change = ExpectedChange.model_validate(
        {"construct": "selected_action", "from": "execute_action", "to": "request_human_review"}
    )
    assert change.from_ == "execute_action"
    assert change.to == "request_human_review"


def test_equals_invariant_requires_value_field() -> None:
    with pytest.raises(ValidationError):
        ExpectedInvariant(construct="escalation", rule="equals")


def test_equals_invariant_allows_explicit_null() -> None:
    invariant = ExpectedInvariant(construct="optional_state", rule="equals", value=None)
    assert invariant.value is None


def test_run_manifest_records_agent_mode_separately_from_identity() -> None:
    manifest = RunManifest(
        run_id="run-1",
        timestamp="2026-09-15T00:00:00Z",
        case_pair_id="auth-001",
        case_pair_version="1",
        artifact_digest="a" * 64,
        canonicalization_version="1",
        execution_source="agent_runner",
        agent_id="reference-agent",
        agent_version="1",
        agent_mode="violate_tool_boundary",
        model=None,
        model_version=None,
        prompt_version=None,
        tool_policy_version="1",
        evaluator_versions={"deterministic": "1"},
        code_sha=None,
        runtime_version="3.11",
    )
    assert manifest.agent_id == "reference-agent"
    assert manifest.agent_mode == "violate_tool_boundary"
