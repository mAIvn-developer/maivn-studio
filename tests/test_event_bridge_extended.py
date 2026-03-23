"""Extended tests for services/event_bridge.py."""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest

from maivn_studio.services.event_bridge import (
    EventBridge,
    StudioEventBridge,
    UIEvent,
    _bridges,
    _safe_json_dumps,
    create_event_bridge,
    get_event_bridge,
    remove_event_bridge,
)

# MARK: Fixtures


@pytest.fixture(autouse=True)
def _clean_bridge_registry() -> Iterator[None]:
    """Ensure bridge registry is clean before and after each test."""
    _bridges.clear()
    yield
    _bridges.clear()


# MARK: UIEvent


class TestUIEvent:
    """Tests for the UIEvent dataclass."""

    def test_post_init_auto_generates_id_and_timestamp(self) -> None:
        event = UIEvent(type="test", data={"k": "v"})

        assert event.id != ""
        assert event.timestamp != ""
        # id should look like a UUID
        assert len(event.id.split("-")) == 5

    def test_post_init_preserves_explicit_values(self) -> None:
        event = UIEvent(type="test", data={}, id="custom-id", timestamp="2025-01-01T00:00:00")

        assert event.id == "custom-id"
        assert event.timestamp == "2025-01-01T00:00:00"

    def test_to_sse_returns_correct_format(self) -> None:
        event = UIEvent(type="tool_event", data={"a": 1}, id="sse-id", timestamp="ts")

        sse = event.to_sse()

        assert sse["event"] == "tool_event"
        assert sse["id"] == "sse-id"
        parsed = json.loads(sse["data"])
        assert parsed["type"] == "tool_event"
        assert parsed["data"] == {"a": 1}
        assert parsed["id"] == "sse-id"
        assert parsed["timestamp"] == "ts"

    def test_to_dict_returns_dict_representation(self) -> None:
        event = UIEvent(type="info", data={"x": 2}, id="d-id", timestamp="ts2")

        d = event.to_dict()

        assert d == {"id": "d-id", "type": "info", "data": {"x": 2}, "timestamp": "ts2"}


# MARK: EventBridge Emit Methods


class TestEventBridgeEmit:
    """Tests for EventBridge emit helper methods."""

    @pytest.mark.asyncio
    async def test_emit_tool_event(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_tool_event(
            tool_name="search",
            tool_id="t1",
            status="completed",
            args={"q": "test"},
            result="found",
            error=None,
            agent_name="agent1",
            swarm_name="swarm1",
            tool_type="func",
        )

        history = bridge.get_history()
        assert len(history) == 1
        assert history[0]["type"] == "tool_event"
        data = history[0]["data"]
        assert data["tool_name"] == "search"
        assert data["tool_id"] == "t1"
        assert data["status"] == "completed"
        assert data["args"] == {"q": "test"}
        assert data["result"] == "found"
        assert data["agent_name"] == "agent1"
        assert data["swarm_name"] == "swarm1"
        assert data["tool_type"] == "func"

    @pytest.mark.asyncio
    async def test_emit_tool_event_defaults(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_tool_event(tool_name="t", tool_id="id", status="pending")

        data = bridge.get_history()[0]["data"]
        assert data["args"] == {}
        assert data["result"] is None
        assert data["tool_type"] == "func"

    @pytest.mark.asyncio
    async def test_emit_system_tool_start(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_system_tool_start(
            tool_type="web_search",
            tool_id="ws1",
            params={"url": "http://test.com"},
            agent_name="a1",
            swarm_name="sw1",
        )

        data = bridge.get_history()[0]["data"]
        assert data["tool_type"] == "web_search"
        assert data["tool_id"] == "ws1"
        assert data["params"] == {"url": "http://test.com"}
        assert data["agent_name"] == "a1"

    @pytest.mark.asyncio
    async def test_emit_system_tool_chunk(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_system_tool_chunk(tool_id="ws1", text="partial", progress=0.5)

        data = bridge.get_history()[0]["data"]
        assert data["tool_id"] == "ws1"
        assert data["text"] == "partial"
        assert data["progress"] == 0.5

    @pytest.mark.asyncio
    async def test_emit_system_tool_complete(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_system_tool_complete(tool_id="ws1", result={"data": "ok"})

        h = bridge.get_history()[0]
        assert h["type"] == "system_tool_complete"
        assert h["data"]["result"] == {"data": "ok"}

    @pytest.mark.asyncio
    async def test_emit_interrupt_required_all_fields(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_interrupt_required(
            interrupt_id="int1",
            data_key="email",
            prompt="Enter your email",
            arg_name="user_email",
            tool_name="collect_info",
            checkpoint_id="cp1",
            assignment_id="a1",
            interrupt_number=2,
            total_interrupts=3,
            input_type="email",
            choices=["a@b.com", "c@d.com"],
        )

        data = bridge.get_history()[0]["data"]
        assert data["interrupt_id"] == "int1"
        assert data["data_key"] == "email"
        assert data["prompt"] == "Enter your email"
        assert data["arg_name"] == "user_email"
        assert data["tool_name"] == "collect_info"
        assert data["checkpoint_id"] == "cp1"
        assert data["assignment_id"] == "a1"
        assert data["interrupt_number"] == 2
        assert data["total_interrupts"] == 3
        assert data["input_type"] == "email"
        assert data["choices"] == ["a@b.com", "c@d.com"]

    @pytest.mark.asyncio
    async def test_emit_interrupt_defaults_arg_name_to_data_key(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_interrupt_required(
            interrupt_id="int2",
            data_key="username",
            prompt="Enter username",
        )

        data = bridge.get_history()[0]["data"]
        assert data["arg_name"] == "username"
        assert data["checkpoint_id"] == ""
        assert data["tool_name"] == ""

    @pytest.mark.asyncio
    async def test_studio_bridge_dedups_interrupts_with_different_ids_for_same_arg(self) -> None:
        bridge = StudioEventBridge("studio-interrupt-dedup")
        await bridge.emit_interrupt_required(
            interrupt_id="live-interrupt-id",
            data_key="live-interrupt-id",
            prompt="Please enter your name:",
            arg_name="user_name",
            tool_name="greet_user",
        )
        await bridge.emit_interrupt_required(
            interrupt_id="replay-interrupt-id",
            data_key="user_name",
            prompt="Please enter your name:",
            arg_name="user_name",
        )

        interrupts = [
            event for event in bridge.get_history() if event["type"] == "interrupt_required"
        ]

        assert len(interrupts) == 1
        assert interrupts[0]["data"]["interrupt_id"] == "live-interrupt-id"
        assert interrupts[0]["data"]["tool_name"] == "greet_user"

    @pytest.mark.asyncio
    async def test_studio_bridge_resets_interrupt_dedup_on_session_start(self) -> None:
        bridge = StudioEventBridge("studio-interrupt-reset")
        await bridge.emit_interrupt_required(
            interrupt_id="interrupt-turn-1",
            data_key="favorite_color",
            prompt="Please enter your favorite color:",
            arg_name="favorite_color",
            tool_name="personalize_profile",
        )
        await bridge.emit("session_start", {"session_id": "studio-interrupt-reset"})
        await bridge.emit_interrupt_required(
            interrupt_id="interrupt-turn-2",
            data_key="favorite_color",
            prompt="Please enter your favorite color:",
            arg_name="favorite_color",
            tool_name="personalize_profile",
        )

        interrupts = [
            event for event in bridge.get_history() if event["type"] == "interrupt_required"
        ]

        assert len(interrupts) == 2
        assert interrupts[0]["data"]["interrupt_id"] == "interrupt-turn-1"
        assert interrupts[1]["data"]["interrupt_id"] == "interrupt-turn-2"

    @pytest.mark.asyncio
    async def test_studio_bridge_dedups_adjacent_identical_status_messages(self) -> None:
        bridge = StudioEventBridge("studio-status-dedup")

        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )
        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )

        status_events = [
            event for event in bridge.get_history() if event["type"] == "status_message"
        ]

        assert len(status_events) == 1
        assert status_events[0]["data"]["message"] == "Planning complete"

    @pytest.mark.asyncio
    async def test_studio_bridge_dedups_identical_status_message_after_other_event(self) -> None:
        bridge = StudioEventBridge("studio-status-repeat")

        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )
        await bridge.emit("enrichment", {"phase": "planning", "message": "Planning actions..."})
        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )

        status_events = [
            event for event in bridge.get_history() if event["type"] == "status_message"
        ]

        assert len(status_events) == 1

    @pytest.mark.asyncio
    async def test_studio_bridge_allows_same_status_again_after_different_status(self) -> None:
        bridge = StudioEventBridge("studio-status-changed")

        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )
        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Synthesizing response"},
        )
        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )

        status_events = [
            event for event in bridge.get_history() if event["type"] == "status_message"
        ]

        assert len(status_events) == 3

    @pytest.mark.asyncio
    async def test_studio_bridge_reopen_resets_status_message_dedup(self) -> None:
        bridge = StudioEventBridge("studio-status-reopen")

        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )
        bridge.reopen()
        await bridge.emit(
            "status_message",
            {"assistant_id": "orchestrator_agent", "message": "Planning complete"},
        )

        status_events = [
            event for event in bridge.get_history() if event["type"] == "status_message"
        ]

        assert len(status_events) == 1
        assert status_events[0]["data"]["message"] == "Planning complete"

    @pytest.mark.asyncio
    async def test_emit_agent_assignment(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_agent_assignment(
            agent_name="researcher",
            status="in_progress",
            assignment_id="asgn1",
            swarm_name="research_swarm",
            task="Find info",
            error=None,
            result=None,
        )

        h = bridge.get_history()[0]
        assert h["type"] == "agent_assignment"
        data = h["data"]
        assert data["agent_name"] == "researcher"
        assert data["status"] == "in_progress"
        assert data["assignment_id"] == "asgn1"
        assert data["swarm_name"] == "research_swarm"
        assert data["task"] == "Find info"

    @pytest.mark.asyncio
    async def test_emit_enrichment_minimal(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_enrichment(phase="evaluating", message="Starting evaluation")

        data = bridge.get_history()[0]["data"]
        assert data["phase"] == "evaluating"
        assert data["message"] == "Starting evaluation"
        assert "scope_id" not in data
        assert "memory" not in data

    @pytest.mark.asyncio
    async def test_emit_enrichment_with_optional_fields(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_enrichment(
            phase="memory_recall",
            message="Recalling context",
            scope_id="agent-1",
            scope_name="Agent One",
            scope_type="agent",
            memory={"recalled": 5},
            redaction={"removed": 2},
        )

        data = bridge.get_history()[0]["data"]
        assert data["scope_id"] == "agent-1"
        assert data["scope_name"] == "Agent One"
        assert data["scope_type"] == "agent"
        assert data["memory"] == {"recalled": 5}
        assert data["redaction"] == {"removed": 2}

    @pytest.mark.asyncio
    async def test_emit_enrichment_ignores_empty_dicts(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_enrichment(
            phase="planning",
            message="Planning",
            memory={},
            redaction={},
        )

        data = bridge.get_history()[0]["data"]
        assert "memory" not in data
        assert "redaction" not in data

    @pytest.mark.asyncio
    async def test_emit_final(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_final(response="Done!", result={"status": "ok"})

        h = bridge.get_history()[0]
        assert h["type"] == "final"
        assert h["data"]["responses"] == ["Done!"]
        assert h["data"]["result"] == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_emit_final_empty_response(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_final(response="   ")

        data = bridge.get_history()[0]["data"]
        assert data["responses"] == []

    @pytest.mark.asyncio
    async def test_emit_error(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_error("Something broke", details={"code": 500})

        h = bridge.get_history()[0]
        assert h["type"] == "error"
        assert h["data"]["error"] == "Something broke"
        assert h["data"]["details"] == {"code": 500}

    @pytest.mark.asyncio
    async def test_emit_error_defaults(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_error("fail")
        assert bridge.get_history()[0]["data"]["details"] == {}

    @pytest.mark.asyncio
    async def test_emit_status_message(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit_status_message(assistant_id="orch", message="Planning complete")

        h = bridge.get_history()[0]
        assert h["type"] == "status_message"
        assert h["data"]["assistant_id"] == "orch"
        assert h["data"]["message"] == "Planning complete"


# MARK: EventBridge State


class TestEventBridgeState:
    """Tests for close, get_history, and closed-bridge behavior."""

    def test_close_marks_bridge_closed(self) -> None:
        bridge = EventBridge("s1")
        assert bridge._closed is False
        bridge.close()
        assert bridge._closed is True

    @pytest.mark.asyncio
    async def test_emit_on_closed_bridge_is_noop(self) -> None:
        bridge = EventBridge("s1")
        bridge.close()
        await bridge.emit("test", {"x": 1})

        assert bridge.get_history() == []

    @pytest.mark.asyncio
    async def test_get_history_returns_event_dicts(self) -> None:
        bridge = EventBridge("s1")
        await bridge.emit("a", {"val": 1})
        await bridge.emit("b", {"val": 2})

        history = bridge.get_history()
        assert len(history) == 2
        assert history[0]["type"] == "a"
        assert history[1]["type"] == "b"
        # Each entry is a dict
        for h in history:
            assert isinstance(h, dict)
            assert "id" in h
            assert "timestamp" in h


# MARK: SSE Replay


class TestEventBridgeSSEReplay:
    """Tests for history replay followed by queued live events."""

    @pytest.mark.asyncio
    async def test_generate_sse_preserves_live_event_order_after_history_replay(self) -> None:
        bridge = EventBridge("s1")
        replayed_one = UIEvent(type="history", data={"step": 1}, id="replayed-1", timestamp="ts-1")
        replayed_two = UIEvent(type="history", data={"step": 2}, id="replayed-2", timestamp="ts-2")
        live_one = UIEvent(type="live", data={"step": 3}, id="live-1", timestamp="ts-3")
        live_two = UIEvent(
            type="final",
            data={"responses": ["done"], "result": None},
            id="live-2",
            timestamp="ts-4",
        )

        bridge._event_history.extend([replayed_one, replayed_two])
        bridge._queue.put_nowait(replayed_one)
        bridge._queue.put_nowait(replayed_two)
        bridge._queue.put_nowait(live_one)
        bridge._queue.put_nowait(live_two)

        events = [event async for event in bridge.generate_sse()]

        assert [event["id"] for event in events] == [
            "replayed-1",
            "replayed-2",
            "live-1",
            "live-2",
        ]


# MARK: Bridge Registry


class TestBridgeRegistry:
    """Tests for create_event_bridge, get_event_bridge, remove_event_bridge."""

    def test_create_and_get(self) -> None:
        bridge = create_event_bridge("sess-1")

        assert isinstance(bridge, EventBridge)
        assert bridge.session_id == "sess-1"
        assert bridge.audience == "internal"
        assert get_event_bridge("sess-1") is bridge

    def test_get_nonexistent_returns_none(self) -> None:
        assert get_event_bridge("missing") is None

    def test_create_closes_existing(self) -> None:
        old = create_event_bridge("sess-1")
        new = create_event_bridge("sess-1")

        assert old._closed is True
        assert new._closed is False
        assert get_event_bridge("sess-1") is new

    def test_remove_closes_and_deletes(self) -> None:
        bridge = create_event_bridge("sess-1")
        remove_event_bridge("sess-1")

        assert bridge._closed is True
        assert get_event_bridge("sess-1") is None

    def test_remove_nonexistent_is_noop(self) -> None:
        remove_event_bridge("nonexistent")  # should not raise


# MARK: _safe_json_dumps


class TestSafeJsonDumps:
    """Tests for _safe_json_dumps()."""

    def test_serializes_normal_dict(self) -> None:
        result = _safe_json_dumps({"key": "value", "num": 42})
        parsed = json.loads(result)
        assert parsed == {"key": "value", "num": 42}

    def test_handles_non_serializable_with_default_str(self) -> None:
        from datetime import datetime

        dt = datetime(2025, 1, 1, 12, 0, 0)
        result = _safe_json_dumps({"ts": dt})
        parsed = json.loads(result)
        assert "2025-01-01" in parsed["ts"]

    def test_handles_serialization_failure(self) -> None:
        """Verify the except branch returns the error fallback."""
        import maivn.events._bridge.serialization as bridge_serialization

        original = bridge_serialization.json.dumps
        call_count = 0

        def patched_dumps(*args: Any, **kwargs: Any) -> str:  # type: ignore[name-defined]
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise TypeError("boom")
            return original(*args, **kwargs)

        bridge_serialization.json.dumps = patched_dumps  # type: ignore[assignment]
        try:
            result = _safe_json_dumps({"will": "fail"})
        finally:
            bridge_serialization.json.dumps = original  # type: ignore[assignment]

        parsed = json.loads(result)
        assert parsed["event"] == "error"
        assert "serialize" in parsed["message"].lower()
