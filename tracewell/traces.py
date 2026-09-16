"""Observable trace helpers for deterministic V1.5 execution.

See docs/ARCHITECTURE.md and ADR-0019.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .models import EventType, Trace, TraceEvent


def evidence_refs(trace: Trace) -> list[str]:
    """Return stable first-seen evidence references from observable events."""
    seen: set[str] = set()
    ordered: list[str] = []
    for event in trace.events:
        for ref in event.evidence_refs:
            if ref not in seen:
                seen.add(ref)
                ordered.append(ref)
    return ordered


def action_from_event(event: TraceEvent) -> str | None:
    """Extract an observable action label without inferring hidden reasoning."""
    if event.event_type == EventType.AGENT_RESPONSE:
        if isinstance(event.output, dict):
            action = event.output.get("action")
            return action if isinstance(action, str) else None
        return event.output if isinstance(event.output, str) else None
    if event.event_type == EventType.TOOL_CALL:
        return event.tool
    if event.event_type == EventType.ESCALATION:
        if isinstance(event.output, dict):
            action = event.output.get("action")
            if isinstance(action, str):
                return action
        return "request_human_review"
    return None


def action_events(trace: Trace) -> list[tuple[int, str, TraceEvent]]:
    """Return ordered observable action events with their event index."""
    values: list[tuple[int, str, TraceEvent]] = []
    for index, event in enumerate(trace.events):
        action = action_from_event(event)
        if action is not None:
            values.append((index, action, event))
    return values


def selected_action(trace: Trace) -> tuple[str | None, list[str]]:
    """Return the final observable action and evidence references."""
    actions = action_events(trace)
    if not actions:
        return None, []
    _, action, event = actions[-1]
    refs = list(event.evidence_refs) or [event.event_id]
    return action, refs


def marker_index(trace: Trace, marker: str) -> int | None:
    """Locate the first explicit identity-bearing fixture marker in the trace."""
    for index, event in enumerate(trace.events):
        if event.metadata.get("fixture_marker") == marker:
            return index
    return None


def revised_after(trace: Trace, marker: str) -> tuple[bool | None, list[str]]:
    """Determine whether an observable action changed after an explicit marker.

    Returns ``None`` when the marker or a before/after action is unavailable,
    allowing the evaluator to preserve uncertainty as REVIEW.
    """
    boundary = marker_index(trace, marker)
    if boundary is None:
        return None, []

    actions = action_events(trace)
    before = [(idx, action, event) for idx, action, event in actions if idx < boundary]
    after = [(idx, action, event) for idx, action, event in actions if idx > boundary]
    if not before or not after:
        return None, []

    _, before_action, before_event = before[-1]
    _, after_action, after_event = after[0]
    refs = [before_event.event_id, trace.events[boundary].event_id, after_event.event_id]
    return before_action != after_action, refs


def trace_event(
    *,
    event_id: str,
    event_type: EventType,
    actor: str | None = None,
    input: Any = None,
    output: Any = None,
    tool: str | None = None,
    tool_arguments: dict[str, Any] | None = None,
    authorization_state: str | None = None,
    evidence_refs: Iterable[str] = (),
    metadata: dict[str, Any] | None = None,
) -> TraceEvent:
    """Construct a TraceEvent with deterministic list/dict defaults."""
    return TraceEvent(
        event_id=event_id,
        event_type=event_type,
        actor=actor,
        input=input,
        output=output,
        tool=tool,
        tool_arguments=tool_arguments,
        authorization_state=authorization_state,
        evidence_refs=list(evidence_refs),
        metadata=dict(metadata or {}),
    )
