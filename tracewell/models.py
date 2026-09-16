"""Canonical V1.5 domain models.

See docs/ARCHITECTURE.md and ADR-0014/0016/0020.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


class EventType(str, Enum):
    USER_MESSAGE = "user_message"
    CONTEXT_RETRIEVAL = "context_retrieval"
    AGENT_RESPONSE = "agent_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ESCALATION = "escalation"


class FindingStatus(str, Enum):
    OPEN = "OPEN"
    MITIGATED = "MITIGATED"
    VERIFYING = "VERIFYING"
    CLOSED = "CLOSED"
    REVIEW = "REVIEW"


JsonScalar = str | int | bool | None


class EvaluationContract(StrictModel):
    required_behaviors: list[str] = Field(default_factory=list)
    prohibited_behaviors: list[str] = Field(default_factory=list)
    required_escalation: bool | None = None
    allowed_tools: list[str] = Field(default_factory=list)
    prohibited_tools: list[str] = Field(default_factory=list)
    required_evidence: list[str] = Field(default_factory=list)


class Case(StrictModel):
    case_id: str
    version: str
    scenario_family: str
    messages: list[dict[str, Any]] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)
    tool_policy: dict[str, Any] = Field(default_factory=dict)
    evaluation_contract: EvaluationContract = Field(default_factory=EvaluationContract)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExpectedChange(StrictModel):
    construct: str
    from_: JsonScalar = Field(alias="from")
    to: JsonScalar

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExpectedInvariant(StrictModel):
    construct: str
    rule: Literal["unchanged", "equals"]
    value: JsonScalar = None
    evidence_refs: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def require_value_for_equals(self) -> "ExpectedInvariant":
        if self.rule == "equals" and "value" not in self.model_fields_set:
            raise ValueError("ExpectedInvariant rule='equals' requires value")
        return self


class CasePair(StrictModel):
    pair_id: str
    version: str
    canonical_case: Case
    perturbed_case: Case
    controlled_variable: str
    expected_changes: list[ExpectedChange] = Field(default_factory=list)
    expected_invariants: list[ExpectedInvariant] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TraceEvent(StrictModel):
    event_id: str
    timestamp: str | None = None
    event_type: EventType
    actor: str | None = None
    input: Any = None
    output: Any = None
    tool: str | None = None
    tool_arguments: dict[str, Any] | None = None
    tool_result: Any = None
    authorization_state: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Trace(StrictModel):
    trace_id: str
    run_id: str
    case_id: str
    events: list[TraceEvent] = Field(default_factory=list)


class EvaluationResult(StrictModel):
    result_id: str
    case_id: str
    evaluator_id: str
    label: Verdict
    construct: str
    observed_value: Any = None
    rationale: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


ConditionEvaluation = list[EvaluationResult]


class ObservedChange(StrictModel):
    construct: str
    canonical_value: Any = None
    perturbed_value: Any = None
    changed: bool
    evidence_refs: list[str] = Field(default_factory=list)


class BehaviorDeltaResult(StrictModel):
    pair_id: str
    canonical_results: ConditionEvaluation = Field(default_factory=list)
    perturbed_results: ConditionEvaluation = Field(default_factory=list)
    expected_changes: list[ExpectedChange] = Field(default_factory=list)
    observed_changes: list[ObservedChange] = Field(default_factory=list)
    expected_invariants: list[ExpectedInvariant] = Field(default_factory=list)
    invariant_violations: list[str] = Field(default_factory=list)
    pair_result: Verdict
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SafetyFinding(StrictModel):
    finding_id: str
    pair_id: str
    case_family: str
    failure_type: str
    expected_changes: list[ExpectedChange] = Field(default_factory=list)
    observed_changes: list[ObservedChange] = Field(default_factory=list)
    invariant_violations: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    proposed_mitigation: str | None = None
    closure_criteria: str | None = None
    verification_run: str | None = None
    status: FindingStatus = FindingStatus.OPEN


class RunManifest(StrictModel):
    run_id: str
    timestamp: str
    case_pair_id: str
    case_pair_version: str
    artifact_digest: str
    canonicalization_version: str
    execution_source: Literal["agent_runner", "trace_source"]
    agent_id: str | None = None
    agent_version: str | None = None
    agent_mode: str | None = None
    model: str | None = None
    model_version: str | None = None
    prompt_version: str | None = None
    tool_policy_version: str | None = None
    evaluator_versions: dict[str, str] = Field(default_factory=dict)
    code_sha: str | None = None
    runtime_version: str
