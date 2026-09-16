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
        if mode in {"respect_late_context", "ignore_late_context"}:
            return self._run_late_context(case, run_id=run_id, mode=mode)

        events = []
        for index, message in enumerate(case.messages):
            events.append(self._message_event(case, index, message))

        action = self._select_action(case, mode)
        events.extend(self._action_events(case, action, suffix="final"))
        return Trace(trace_id=f"{run_id}:{case.case_id}", run_id=run_id, case_id=case.case_id, events=events)

    def _run_late_context(self, case: Case, *, run_id: str, mode: AgentMode) -> Trace:
        events = []
        marker_seen = False
        initial_action = str(case.context.get("required_action", "continue"))
        late_action = str(case.context.get("late_context_action", "request_human_review"))

        for index, message in enumerate(case.messages):
            marker = message.get("fixture_marker") if isinstance(message, dict) else None
            if isinstance(marker, str) and not marker_seen:
                if not any(e.event_type in {EventType.AGENT_RESPONSE, EventType.ESCALATION, EventType.TOOL_CALL} for e in events):
                    events.extend(self._action_events(case, initial_action, suffix="pre"))
                marker_seen = True
            events.append(self._message_event(case, index, message))

        if marker_seen:
            final_action = late_action if mode == "respect_late_context" else initial_action
            events.extend(self._action_events(case, final_action, suffix="post"))
        else:
            events.extend(self._action_events(case, initial_action, suffix="final"))

        return Trace(trace_id=f"{run_id}:{case.case_id}", run_id=run_id, case_id=case.case_id, events=events)

    def _message_event(self, case: Case, index: int, message: dict):
        metadata = {}
        if isinstance(message, dict) and isinstance(message.get("fixture_marker"), str):
            metadata["fixture_marker"] = message["fixture_marker"]
        return trace_event(
            event_id=f"{case.case_id}:msg:{index}",
            event_type=EventType.USER_MESSAGE,
            actor=str(message.get("role", "user")) if isinstance(message, dict) else "user",
            input=message,
            metadata=metadata,
        )

    def _select_action(self, case: Case, mode: AgentMode) -> str:
        context_action = str(case.context.get("required_action", "continue"))
        contradiction_action = str(case.context.get("contradiction_action", "clarify"))

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

    def _action_events(self, case: Case, action: str, *, suffix: str):
        if action == "request_human_review":
            event_id = f"{case.case_id}:escalation:{suffix}"
            return [
                trace_event(
                    event_id=event_id,
                    event_type=EventType.ESCALATION,
                    actor="agent",
                    output={"action": action},
                    evidence_refs=[event_id],
                )
            ]

        requested_tool = str(case.tool_policy.get("requested_tool", "execute_action"))
        if action == requested_tool:
            event_id = f"{case.case_id}:tool:{suffix}"
            authorized = self._tool_authorized(case)
            return [
                trace_event(
                    event_id=event_id,
                    event_type=EventType.TOOL_CALL,
                    actor="agent",
                    tool=action,
                    tool_arguments=dict(case.tool_policy.get("tool_arguments", {})),
                    authorization_state="allowed" if authorized else "prohibited",
                    evidence_refs=[event_id],
                )
            ]

        event_id = f"{case.case_id}:response:{suffix}"
        return [
            trace_event(
                event_id=event_id,
                event_type=EventType.AGENT_RESPONSE,
                actor="agent",
                output={"action": action},
                evidence_refs=[event_id],
            )
        ]
