from __future__ import annotations

import pytest

from tracewell.models import EventType
from tracewell.tau3_adapter import (
    Tau3AdapterError,
    normalize_tau3_simulation,
    to_tracewell_trace,
)


def _telemetry(**overrides):
    base = {
        "tool_name": "update_reservation_flights",
        "execution_started": True,
        "execution_succeeded": True,
        "state_before": {"reservations": {"R123": {"flight": "late"}}},
        "state_after": {"reservations": {"R123": {"flight": "early"}}},
        "state_delta": {"reservations.R123.flight": ["late", "early"]},
        "changed_reservation_ids": ["R123"],
    }
    base.update(overrides)
    return base


def test_normalizes_nested_tool_message_and_preserves_role():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "update_reservation_flights",
                        "arguments": {"reservation_id": "R123"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_messages": [
                    {
                        "id": "call-1",
                        "content": '{"ok": true}',
                        "error": False,
                    }
                ],
            },
        ]
    }

    trajectory = normalize_tau3_simulation(
        simulation,
        telemetry={"call-1": _telemetry()},
        run_id="run-1",
        task_id="task-1",
        variant_id="A",
    )

    assert [event.event_type for event in trajectory.events] == [
        "tool_call",
        "state_change",
        "tool_result",
    ]
    assert trajectory.events[-1].actor == "tool"
    assert trajectory.events[-1].raw_event_ref == "messages[1].tool_messages[0]"


def test_missing_tool_telemetry_is_rejected():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call-1", "name": "get_reservation_details", "arguments": {}}
                ],
            }
        ]
    }

    with pytest.raises(Tau3AdapterError, match="no instrumentation telemetry"):
        normalize_tau3_simulation(
            simulation,
            telemetry={},
            run_id="run-1",
            task_id="task-1",
            variant_id="A",
        )


def test_missing_tool_call_id_is_rejected_instead_of_falling_back():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"name": "get_reservation_details", "arguments": {}}
                ],
            }
        ]
    }

    with pytest.raises(Tau3AdapterError, match="missing tool_call id"):
        normalize_tau3_simulation(
            simulation,
            telemetry={},
            run_id="run-1",
            task_id="task-1",
            variant_id="A",
        )


def test_unknown_execution_started_remains_unknown():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": "call-1", "name": "get_reservation_details", "arguments": {}}
                ],
            },
            {
                "role": "tool",
                "id": "call-1",
                "content": "{}",
                "error": False,
            },
        ]
    }

    trajectory = normalize_tau3_simulation(
        simulation,
        telemetry={
            "call-1": {
                "tool_name": "get_reservation_details",
                "execution_succeeded": True,
            }
        },
        run_id="run-1",
        task_id="task-1",
        variant_id="A",
    )

    assert trajectory.events[0].tool_execution_started is None
    assert trajectory.events[1].tool_execution_started is None


def test_empty_content_message_is_preserved():
    simulation = {"messages": [{"role": "user", "content": ""}]}

    trajectory = normalize_tau3_simulation(
        simulation,
        telemetry={},
        run_id="run-1",
        task_id="task-1",
        variant_id="A",
    )

    assert len(trajectory.events) == 1
    assert trajectory.events[0].event_type == "message"
    assert trajectory.events[0].content == ""
    assert trajectory.events[0].metadata["empty_content"] is True


def test_malformed_tool_call_reports_context():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": ["not-a-mapping"],
            }
        ]
    }

    with pytest.raises(Tau3AdapterError, match=r"messages\[0\]\.tool_calls\[0\]"):
        normalize_tau3_simulation(
            simulation,
            telemetry={},
            run_id="run-1",
            task_id="task-1",
            variant_id="A",
        )


def test_arguments_null_stays_null():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [{"id": "call-1", "name": "noop", "arguments": None}],
            }
        ]
    }

    trajectory = normalize_tau3_simulation(
        simulation,
        telemetry={"call-1": {"tool_name": "noop"}},
        run_id="run-1",
        task_id="task-1",
        variant_id="A",
    )

    assert trajectory.events[0].arguments is None


def test_projection_preserves_normalized_state_change_type_and_evidence():
    simulation = {
        "messages": [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call-1",
                        "name": "update_reservation_flights",
                        "arguments": {"reservation_id": "R123"},
                    }
                ],
            }
        ]
    }
    trajectory = normalize_tau3_simulation(
        simulation,
        telemetry={"call-1": _telemetry()},
        run_id="run-1",
        task_id="task-1",
        variant_id="A",
    )

    trace = to_tracewell_trace(trajectory)
    assert trace.events[0].event_type == EventType.TOOL_CALL
    assert trace.events[1].event_type == EventType.TOOL_RESULT
    assert trace.events[1].metadata["normalized_event_type"] == "state_change"
    assert trace.events[1].metadata["state_delta"]
    assert trace.events[1].event_id.endswith("000001")
