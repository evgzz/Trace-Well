"""Deterministic reference agent for V1.5 mechanism tests.

See ADR-0014 and docs/BENCHMARK_DESIGN.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .models import Case, EventType, Trace
from .traces import trace_event

AgentMode = Literal[
    "respect_context",
    "ignore_context",
    "detect_contradiction",
    "ignore_contradiction",
    "respect_tool_boundary",
    "violate_tool_boundary",
    "respect_late_context",
    "ignore_late_context",
    "always_escalate",
]


@dataclass(frozen=True)
class ReferenceAgent:
    agent_id: str = "tracewell.reference"
    agent_version: str = "1.0"

    def run(self, case: Case, *, run_id: str, mode: AgentMode) -> Trace:
        events = []

        for index, message in enumerate(case.messages):
            metadata = {}
            if isinstance(message, dict) and isinstance(message.get("fixture_marker"), str):
                metadata["fixture_marker"] = message["fixture_marker"]
            events.append(
                trace_event(
                    event_id=f"{case.case_id}:msg:{index}",
                    event_type=EventType.USER_MESSAGE,
                    actor=str(message.get("role", "user")) if isinstance(message, dict) else "user",
                    input=message,
                    metadata=metadata,
                )
            )

        action = self._select_action(case, mode)
        events.extend(self._action_events(case, action))
        return Trace(trace_id=f"{run_id}:{case.case_id}", run_id=run_id, case_id=case.case_id, events=events)

    def _select_action(self, case: Case, mode: AgentMode) -> str:
        context_action = str(case.context.get("required_action", "continue"))
        contradiction_action = str(case.context.get("contradiction_action", "clarify"))
        late_action = str(case.context.get("late_context_action", "request_human_review"))

        if mode == "always_escalate":
            return "request_human_review"
        if mode == "respect_context":
            return context_action
        if mode == "ignore_context":
            return str(case.context.get("default_action", "continue"))
        if mode == "detect_contradiction":
            return contradiction_action if bool(case.context.get("contradiction")) else context_action
        if mode == "ignore_contradiction":
            return context_action
        if mode == "respect_late_context":
            return late_action if bool(case.context.get("late_context_present")) else context_action
        if mode == "ignore_late_context":
            return context_action
        if mode == "respect_tool_boundary":
            if self._tool_authorized(case):
                return str(case.tool_policy.get("requested_tool", "execute_action"))
            return "request_human_review"
        if mode == "violate_tool_boundary":
            return str(case.tool_policy.get("requested_tool", "execute_action"))
        raise ValueError(f"Unsupported agent mode: {mode}")

    @staticmethod
    def _tool_authorized(case: Case) -> bool:
        requested = str(case.tool_policy.get("requested_tool", "execute_action"))
        allowed = {str(v) for v in case.tool_policy.get("allowed_tools", [])}
        prohibited = {str(v) for v in case.tool_policy.get("prohibited_tools", [])}
        if requested in prohibited:
            return False
        return requested in allowed

    def _action_events(self, case: Case, action: str):
        if action == "request_human_review":
            return [
                trace_event(
                    event_id=f"{case.case_id}:escalation",
                    event_type=EventType.ESCALATION,
                    actor="agent",
                    output={"action": action},
                    evidence_refs=[f"{case.case_id}:escalation"],
                )
            ]

        requested_tool = str(case.tool_policy.get("requested_tool", "execute_action"))
        if action == requested_tool:
            authorized = self._tool_authorized(case)
            return [
                trace_event(
                    event_id=f"{case.case_id}:tool",
                    event_type=EventType.TOOL_CALL,
                    actor="agent",
                    tool=action,
                    tool_arguments=dict(case.tool_policy.get("tool_arguments", {})),
                    authorization_state="allowed" if authorized else "prohibited",
                    evidence_refs=[f"{case.case_id}:tool"],
                )
            ]

        return [
            trace_event(
                event_id=f"{case.case_id}:response",
                event_type=EventType.AGENT_RESPONSE,
                actor="agent",
                output={"action": action},
                evidence_refs=[f"{case.case_id}:response"],
            )
        ]
