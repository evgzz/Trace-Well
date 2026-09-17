"""Thin τ³-bench -> TRACE-Well trajectory adapter.

τ³ remains an optional experiment dependency. This module accepts plain mappings
(or Pydantic models via model_dump), normalizes τ³ evidence into an
experiment-local schema, and only then projects that evidence into TRACE-Well's
frozen Trace/TraceEvent schema.

Evidence rule: tool execution and state mutation are established from explicit
instrumentation telemetry, never inferred from assistant text or tool wording.
"""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import Field

from .models import EventType, StrictModel, Trace, TraceEvent


NormalizedEventType = Literal["message", "tool_call", "tool_result", "state_change"]


class Tau3AdapterError(ValueError):
    """Raised when τ³ evidence cannot be normalized without guessing."""


class Tau3NormalizedEvent(StrictModel):
    sequence: int
    actor: Literal["user", "agent", "tool", "environment"]
    event_type: NormalizedEventType
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    content: Any = None
    state_before: dict[str, Any] | None = None
    state_after: dict[str, Any] | None = None
    state_delta: dict[str, Any] | None = None
    tool_execution_started: bool | None = None
    tool_execution_succeeded: bool | None = None
    raw_event_ref: str
    timestamp: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Tau3NormalizedTrajectory(StrictModel):
    run_id: str
    task_id: str
    variant_id: str
    events: list[Tau3NormalizedEvent] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)


def _as_mapping(value: Any, *, context: str) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception as exc:
            raise Tau3AdapterError(
                f"{context}: model_dump(mode='json') failed: {exc}"
            ) from exc
    raise Tau3AdapterError(
        f"{context}: expected mapping-compatible value, got {type(value)!r}"
    )


def _flatten_messages(
    messages: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str]]:
    """Flatten MultiToolMessage-like containers without losing source identity."""

    flattened: list[tuple[dict[str, Any], str]] = []
    for message_index, message in enumerate(messages):
        parent_ref = f"messages[{message_index}]"
        nested = message.get("tool_messages")
        if nested is None:
            flattened.append((message, parent_ref))
            continue
        if not isinstance(nested, list):
            raise Tau3AdapterError(f"{parent_ref}.tool_messages: expected list")
        for tool_index, item in enumerate(nested):
            item_ref = f"{parent_ref}.tool_messages[{tool_index}]"
            tool_message = _as_mapping(item, context=item_ref)
            role = tool_message.get("role")
            if role not in (None, "tool"):
                raise Tau3AdapterError(
                    f"{item_ref}: nested tool message has unexpected role {role!r}"
                )
            tool_message["role"] = "tool"
            flattened.append((tool_message, item_ref))
    return flattened


def _require_tool_telemetry(
    telemetry_by_id: Mapping[str, Mapping[str, Any]],
    *,
    call_id: str,
    context: str,
) -> dict[str, Any]:
    telemetry = telemetry_by_id.get(call_id)
    if telemetry is None:
        raise Tau3AdapterError(
            f"{context}: no instrumentation telemetry for tool_call id {call_id!r}; "
            "refusing to infer execution/state evidence"
        )
    return dict(telemetry)


def normalize_tau3_simulation(
    simulation: Mapping[str, Any] | Any,
    *,
    telemetry: Mapping[str, Mapping[str, Any]] | None,
    run_id: str,
    task_id: str,
    variant_id: str,
    provenance: Mapping[str, Any] | None = None,
) -> Tau3NormalizedTrajectory:
    """Normalize one half-duplex τ³ SimulationRun.

    Instrumentation telemetry is mandatory for every tool call/result. It is the
    authoritative source for execution and before/after state. Unknown values
    remain None; this adapter does not upgrade missing evidence into a fact.
    """

    raw = _as_mapping(simulation, context="simulation")
    raw_message_values = raw.get("messages")
    if raw_message_values is None:
        raw_message_values = []
    if not isinstance(raw_message_values, list):
        raise Tau3AdapterError("simulation.messages: expected list")

    raw_messages = [
        _as_mapping(item, context=f"messages[{index}]")
        for index, item in enumerate(raw_message_values)
    ]
    messages = _flatten_messages(raw_messages)

    telemetry_by_id: dict[str, dict[str, Any]] = {}
    for key, value in (telemetry or {}).items():
        telemetry_by_id[str(key)] = _as_mapping(
            value, context=f"telemetry[{key!r}]"
        )

    events: list[Tau3NormalizedEvent] = []
    sequence = 0

    for flat_index, (message, raw_ref) in enumerate(messages):
        role = message.get("role")
        if role not in {"user", "assistant", "tool"}:
            raise Tau3AdapterError(
                f"{raw_ref}: unsupported or missing role {role!r} "
                f"(flattened index {flat_index})"
            )

        timestamp = message.get("timestamp")
        content_present = "content" in message
        content = message.get("content")

        if role in {"user", "assistant"} and content_present and content is not None:
            actor: Literal["user", "agent"] = "user" if role == "user" else "agent"
            events.append(
                Tau3NormalizedEvent(
                    sequence=sequence,
                    actor=actor,
                    event_type="message",
                    content=content,
                    raw_event_ref=raw_ref,
                    timestamp=timestamp,
                    evidence_refs=[raw_ref],
                    metadata={"empty_content": content == ""},
                )
            )
            sequence += 1

        if role in {"user", "assistant"}:
            tool_calls = message.get("tool_calls") or []
            if not isinstance(tool_calls, list):
                raise Tau3AdapterError(f"{raw_ref}.tool_calls: expected list")
            for call_index, call_value in enumerate(tool_calls):
                call_ref = f"{raw_ref}.tool_calls[{call_index}]"
                call = _as_mapping(call_value, context=call_ref)

                raw_call_id = call.get("id")
                if not raw_call_id:
                    raise Tau3AdapterError(
                        f"{call_ref}: missing tool_call id; deterministic telemetry "
                        "correlation is required"
                    )
                call_id = str(raw_call_id)
                tel = _require_tool_telemetry(
                    telemetry_by_id, call_id=call_id, context=call_ref
                )

                raw_tool_name = call.get("name")
                if not raw_tool_name:
                    raise Tau3AdapterError(f"{call_ref}: missing tool name")
                tool_name = str(raw_tool_name)

                raw_arguments = call.get("arguments") if "arguments" in call else None
                if raw_arguments is None:
                    arguments = None
                elif isinstance(raw_arguments, Mapping):
                    arguments = dict(raw_arguments)
                else:
                    raise Tau3AdapterError(
                        f"{call_ref}.arguments: expected mapping or null, "
                        f"got {type(raw_arguments)!r}"
                    )

                events.append(
                    Tau3NormalizedEvent(
                        sequence=sequence,
                        actor="user" if role == "user" else "agent",
                        event_type="tool_call",
                        tool_name=tool_name,
                        arguments=arguments,
                        state_before=tel.get("state_before"),
                        state_after=tel.get("state_after"),
                        state_delta=tel.get("state_delta"),
                        tool_execution_started=tel.get("execution_started"),
                        tool_execution_succeeded=tel.get("execution_succeeded"),
                        raw_event_ref=call_ref,
                        timestamp=timestamp,
                        evidence_refs=[call_ref, *list(tel.get("evidence_refs") or [])],
                        metadata={
                            "tool_call_id": call_id,
                            "requestor": call.get("requestor", role),
                            "authorization_valid": tel.get("authorization_valid"),
                            "changed_reservation_ids": list(
                                tel.get("changed_reservation_ids") or []
                            ),
                            "injected_content": bool(
                                tel.get("injected_content", False)
                            ),
                            "failure_injected": bool(
                                tel.get("failure_injected", False)
                            ),
                        },
                    )
                )
                sequence += 1

                if tel.get("state_delta"):
                    state_ref = f"telemetry[{call_id}].state_delta"
                    events.append(
                        Tau3NormalizedEvent(
                            sequence=sequence,
                            actor="environment",
                            event_type="state_change",
                            tool_name=tool_name,
                            arguments=arguments,
                            state_before=tel.get("state_before"),
                            state_after=tel.get("state_after"),
                            state_delta=tel.get("state_delta"),
                            tool_execution_started=tel.get("execution_started"),
                            tool_execution_succeeded=tel.get("execution_succeeded"),
                            raw_event_ref=state_ref,
                            timestamp=timestamp,
                            evidence_refs=[state_ref],
                            metadata={
                                "tool_call_id": call_id,
                                "changed_reservation_ids": list(
                                    tel.get("changed_reservation_ids") or []
                                ),
                            },
                        )
                    )
                    sequence += 1

        if role == "tool":
            raw_call_id = message.get("id")
            if not raw_call_id:
                raise Tau3AdapterError(
                    f"{raw_ref}: tool result missing correlation id"
                )
            call_id = str(raw_call_id)
            tel = _require_tool_telemetry(
                telemetry_by_id, call_id=call_id, context=raw_ref
            )

            error = bool(message.get("error", False))
            execution_succeeded = tel.get("execution_succeeded")
            if execution_succeeded is None and "error" in message:
                execution_succeeded = not error

            events.append(
                Tau3NormalizedEvent(
                    sequence=sequence,
                    actor="tool",
                    event_type="tool_result",
                    tool_name=tel.get("tool_name"),
                    content=content,
                    state_before=tel.get("state_before"),
                    state_after=tel.get("state_after"),
                    state_delta=tel.get("state_delta"),
                    tool_execution_started=tel.get("execution_started"),
                    tool_execution_succeeded=execution_succeeded,
                    raw_event_ref=raw_ref,
                    timestamp=timestamp,
                    evidence_refs=[raw_ref, *list(tel.get("evidence_refs") or [])],
                    metadata={
                        "tool_call_id": call_id,
                        "error": error if "error" in message else None,
                        "injected_content": bool(
                            tel.get("injected_content", False)
                        ),
                        "failure_injected": bool(
                            tel.get("failure_injected", False)
                        ),
                        "changed_reservation_ids": list(
                            tel.get("changed_reservation_ids") or []
                        ),
                    },
                )
            )
            sequence += 1

    return Tau3NormalizedTrajectory(
        run_id=run_id,
        task_id=task_id,
        variant_id=variant_id,
        events=events,
        provenance=dict(provenance or {}),
    )


def to_tracewell_trace(
    trajectory: Tau3NormalizedTrajectory,
    *,
    case_id: str | None = None,
) -> Trace:
    """Project normalized τ³ evidence into the frozen TRACE-Well Trace schema."""

    projected: list[TraceEvent] = []
    for event in trajectory.events:
        if event.event_type == "message":
            event_type = (
                EventType.USER_MESSAGE
                if event.actor == "user"
                else EventType.AGENT_RESPONSE
            )
        elif event.event_type == "tool_call":
            event_type = EventType.TOOL_CALL
        else:
            event_type = EventType.TOOL_RESULT

        metadata = {
            "sequence": event.sequence,
            "normalized_event_type": event.event_type,
            "state_before": event.state_before,
            "state_after": event.state_after,
            "state_delta": event.state_delta,
            "tool_execution_started": event.tool_execution_started,
            "tool_execution_succeeded": event.tool_execution_succeeded,
            "raw_event_ref": event.raw_event_ref,
            **event.metadata,
        }
        projected.append(
            TraceEvent(
                event_id=f"{trajectory.run_id}:event:{event.sequence:06d}",
                timestamp=event.timestamp,
                event_type=event_type,
                actor=event.actor,
                input=event.content if event.actor == "user" else None,
                output=event.content if event.actor in {"agent", "tool"} else None,
                tool=event.tool_name,
                tool_arguments=event.arguments,
                tool_result=(
                    event.content if event.event_type == "tool_result" else None
                ),
                evidence_refs=event.evidence_refs,
                metadata=metadata,
            )
        )

    return Trace(
        trace_id=f"{trajectory.run_id}:trace",
        run_id=trajectory.run_id,
        case_id=case_id or trajectory.variant_id,
        events=projected,
    )
