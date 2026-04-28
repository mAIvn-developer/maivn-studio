"""Extended tests for StudioReporter covering no-op methods, phase changes,
tool reporting, enrichment, streaming deltas, and submit handling."""

from __future__ import annotations

import asyncio
import gc
from typing import Any

import pytest
from maivn._internal.utils.reporting.context import current_sdk_delivery_mode
from maivn._internal.utils.reporting.terminal_reporter.event_router.reporter import (
    EventRouterReporter,
)

from maivn_studio.services.event_bridge import EventBridge
from maivn_studio.services.studio_reporter.reporter import StudioReporter


def StudioEventBridge(session_id: str) -> EventBridge:  # noqa: N802
    """Test factory matching Studio's runtime bridge configuration."""
    return EventBridge(
        session_id,
        audience="internal",
        dedupe_status_messages=True,
    )


# MARK: Helpers


def _make_pair() -> tuple[EventBridge, StudioReporter]:
    """Create a fresh EventBridge and StudioReporter on the running loop."""
    bridge = EventBridge("test-session")
    loop = asyncio.get_running_loop()
    reporter = StudioReporter(bridge=bridge, loop=loop)
    return bridge, reporter


async def _drain() -> None:
    """Give threadsafe-submitted coroutines a chance to execute."""
    await asyncio.sleep(0.05)


def _events_of_type(bridge: EventBridge, event_type: str) -> list[dict[str, Any]]:
    return [e for e in bridge.get_history() if e.get("type") == event_type]


# MARK: No-op Methods


class TestNoOpMethods:
    @pytest.mark.asyncio
    async def test_print_header(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_header("Title", "Subtitle") is None

    @pytest.mark.asyncio
    async def test_print_section(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_section("Section") is None

    @pytest.mark.asyncio
    async def test_print_event(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_event("type", "message", {"key": "val"}) is None

    @pytest.mark.asyncio
    async def test_print_summary(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_summary({"tokens": 100}) is None

    @pytest.mark.asyncio
    async def test_print_final_result(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_final_result({"answer": 42}) is None

    @pytest.mark.asyncio
    async def test_print_final_response(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_final_response("done") is None

    @pytest.mark.asyncio
    async def test_print_error_summary(self) -> None:
        _, reporter = _make_pair()
        assert reporter.print_error_summary("oops") is None

    @pytest.mark.asyncio
    async def test_update_progress(self) -> None:
        _, reporter = _make_pair()
        assert reporter.update_progress("task-1", "doing stuff") is None

    @pytest.mark.asyncio
    async def test_report_session_start(self) -> None:
        _, reporter = _make_pair()
        assert reporter.report_session_start("s1", "a1") is None

    @pytest.mark.asyncio
    async def test_report_private_data(self) -> None:
        _, reporter = _make_pair()
        assert reporter.report_private_data({"key": "secret"}) is None


# MARK: Context Managers


class TestContextManagers:
    @pytest.mark.asyncio
    async def test_live_progress_yields_none(self) -> None:
        _, reporter = _make_pair()
        with reporter.live_progress("Loading...") as ctx:
            assert ctx is None

    @pytest.mark.asyncio
    async def test_prepare_for_user_input_yields(self) -> None:
        _, reporter = _make_pair()
        entered = False
        with reporter.prepare_for_user_input():
            entered = True
        assert entered is True


# MARK: Interrupt Input


class _ImmediateInterruptEvent:
    def wait(self, timeout: float | None = None) -> bool:
        _ = timeout
        return True


def _register_immediate_interrupt(
    _interrupt_id: str,
    *,
    aliases: list[str] | None = None,
) -> _ImmediateInterruptEvent:
    _ = aliases
    return _ImmediateInterruptEvent()


class TestInterruptInput:
    @pytest.mark.asyncio
    async def test_get_input_registers_session_scoped_alias_for_data_key(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bridge = StudioEventBridge("interrupt-alias-session")
        reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())
        captured: dict[str, Any] = {}

        def _register_interrupt(
            interrupt_id: str,
            *,
            aliases: list[str] | None = None,
        ) -> _ImmediateInterruptEvent:
            captured["interrupt_id"] = interrupt_id
            captured["aliases"] = aliases
            return _ImmediateInterruptEvent()

        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.register_interrupt",
            _register_interrupt,
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.get_interrupt_response",
            lambda _interrupt_id: "Chad",
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.cleanup_interrupt",
            lambda _interrupt_id: None,
        )

        result = reporter.get_input(
            "Please enter your name: ",
            data_key="user_name",
            arg_name="user_name",
        )

        assert result == "Chad"
        assert captured["aliases"] == ["interrupt-alias-session:user_name"]

    @pytest.mark.asyncio
    async def test_get_input_uses_logical_field_name_for_bridge_dedup(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bridge = StudioEventBridge("interrupt-dedup-session")
        reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())

        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.register_interrupt",
            _register_immediate_interrupt,
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.get_interrupt_response",
            lambda _interrupt_id: "Chad",
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.cleanup_interrupt",
            lambda _interrupt_id: None,
        )

        reporter.report_tool_start(
            tool_name="greet_user",
            event_id="tool-1",
            tool_type="func",
        )
        result = reporter.get_input(
            "Please enter your name: ",
            arg_name="user_name",
        )
        await _drain()

        await bridge.emit_interrupt_required(
            interrupt_id="replay-interrupt-id",
            data_key="user_name",
            prompt="Please enter your name:",
            arg_name="user_name",
        )

        interrupts = _events_of_type(bridge, "interrupt_required")

        assert result == "Chad"
        assert len(interrupts) == 1
        assert interrupts[0]["data"]["data_key"] == "user_name"
        assert interrupts[0]["data"]["tool_name"] == "greet_user"

    @pytest.mark.asyncio
    async def test_event_router_preserves_interrupt_identity_metadata(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        bridge = StudioEventBridge("interrupt-router-session")
        base_reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())
        reporter = EventRouterReporter(base_reporter)

        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.register_interrupt",
            _register_immediate_interrupt,
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.get_interrupt_response",
            lambda _interrupt_id: "Chad",
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.reporter.cleanup_interrupt",
            lambda _interrupt_id: None,
        )

        reporter.report_tool_start(
            tool_name="greet_user",
            event_id="tool-1",
            tool_type="func",
        )
        result = reporter.get_input(
            "Please enter your name: ",
            data_key="user_name",
            arg_name="user_name",
        )
        await _drain()

        await bridge.emit_interrupt_required(
            interrupt_id="replay-interrupt-id",
            data_key="user_name",
            prompt="Please enter your name:",
            arg_name="user_name",
        )

        interrupts = _events_of_type(bridge, "interrupt_required")

        assert result == "Chad"
        assert len(interrupts) == 1
        assert interrupts[0]["data"]["data_key"] == "user_name"
        assert interrupts[0]["data"]["tool_name"] == "greet_user"


# MARK: Phase Changes


class TestReportPhaseChange:
    @pytest.mark.asyncio
    async def test_known_phase_planning(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_phase_change("planning")
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert len(events) == 1
        assert events[0]["data"]["phase"] == "planning"
        assert events[0]["data"]["message"] == "Planning actions..."

    @pytest.mark.asyncio
    async def test_known_phase_synthesizing(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_phase_change("synthesizing")
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert len(events) == 1
        assert events[0]["data"]["message"] == "Synthesizing response..."

    @pytest.mark.asyncio
    async def test_unknown_phase_capitalized(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_phase_change("custom_phase")
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert len(events) == 1
        assert events[0]["data"]["phase"] == "custom_phase"
        assert events[0]["data"]["message"] == "Custom phase..."

    @pytest.mark.asyncio
    async def test_empty_phase_ignored(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_phase_change("")
        reporter.report_phase_change("   ")
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert len(events) == 0


# MARK: Tool Start


class TestReportToolStart:
    @pytest.mark.asyncio
    async def test_system_tool_start(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="web_search",
            event_id="ev-1",
            tool_type="system",
            agent_name="agent-1",
            tool_args={"query": "test"},
        )
        await _drain()
        events = _events_of_type(bridge, "system_tool_start")
        assert len(events) == 1
        assert events[0]["data"]["tool_type"] == "web_search"
        assert events[0]["data"]["tool_id"] == "ev-1"

    @pytest.mark.asyncio
    async def test_regular_tool_start(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="my_func",
            event_id="ev-2",
            tool_type="func",
            agent_name="agent-1",
            tool_args={"x": 1},
        )
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["tool_name"] == "my_func"
        assert events[0]["data"]["status"] == "executing"

    @pytest.mark.asyncio
    async def test_default_tool_type_is_func(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="my_func",
            event_id="ev-3",
            tool_type=None,
        )
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["tool_type"] == "func"


# MARK: Tool Complete


class TestReportToolComplete:
    @pytest.mark.asyncio
    async def test_system_tool_complete(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="web_search",
            event_id="ev-1",
            tool_type="system",
        )
        await _drain()
        reporter.report_tool_complete(event_id="ev-1", result="search results")
        await _drain()
        events = _events_of_type(bridge, "system_tool_complete")
        assert len(events) == 1
        assert events[0]["data"]["result"] == "search results"

    @pytest.mark.asyncio
    async def test_system_tool_complete_in_contract_stream_mode(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="web_search",
            event_id="ev-1",
            tool_type="system",
        )
        await _drain()
        token = current_sdk_delivery_mode.set("stream")
        try:
            reporter.report_tool_complete(event_id="ev-1", result="search results")
        finally:
            current_sdk_delivery_mode.reset(token)
        await _drain()
        events = _events_of_type(bridge, "system_tool_complete")
        assert len(events) == 1
        assert events[0]["data"]["result"] == "search results"

    @pytest.mark.asyncio
    async def test_regular_tool_complete(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="my_func",
            event_id="ev-2",
            tool_type="func",
        )
        await _drain()
        reporter.report_tool_complete(event_id="ev-2", result="ok")
        await _drain()
        tool_events = _events_of_type(bridge, "tool_event")
        completed = [e for e in tool_events if e["data"]["status"] == "completed"]
        assert len(completed) == 1
        assert completed[0]["data"]["result"] == "ok"

    @pytest.mark.asyncio
    async def test_unknown_tool_id_complete(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_complete(event_id="unknown-id", result="data")
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["status"] == "completed"


# MARK: Tool Error


class TestReportToolError:
    @pytest.mark.asyncio
    async def test_emits_failure(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_error(
            tool_name="bad_tool",
            error="Something broke",
            event_id="ev-err",
        )
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["status"] == "failed"
        assert events[0]["data"]["error"] == "Something broke"

    @pytest.mark.asyncio
    async def test_uses_tool_name_as_fallback_id(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_error(
            tool_name="bad_tool",
            error="err",
            event_id=None,
        )
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert events[0]["data"]["tool_id"] == "bad_tool"


# MARK: Model Tool Complete


class TestReportModelToolComplete:
    @pytest.mark.asyncio
    async def test_emits_model_completion(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_model_tool_complete(
            tool_name="model_tool",
            event_id="mt-1",
            agent_name="agent-1",
            swarm_name="swarm-1",
            result={"key": "value"},
        )
        await _drain()
        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["tool_type"] == "model"
        assert events[0]["data"]["status"] == "completed"
        assert events[0]["data"]["agent_name"] == "agent-1"


# MARK: Agent Assignment


class TestReportAgentAssignment:
    @pytest.mark.asyncio
    async def test_emits_assignment(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_agent_assignment(
            agent_name="researcher",
            status="received",
            assignment_id="a-1",
            swarm_name="main_swarm",
        )
        await _drain()
        events = _events_of_type(bridge, "agent_assignment")
        assert len(events) == 1
        assert events[0]["data"]["agent_name"] == "researcher"
        assert events[0]["data"]["status"] == "received"
        assert events[0]["data"]["swarm_name"] == "main_swarm"


# MARK: Enrichment


class TestReportEnrichment:
    @pytest.mark.asyncio
    async def test_normalizes_scope_type(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="test",
            message="msg",
            scope_type="  Agent  ",
            scope_id="  agent-1  ",
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert events[0]["data"]["scope_type"] == "agent"
        assert events[0]["data"]["scope_id"] == "agent-1"

    @pytest.mark.asyncio
    async def test_rejects_invalid_scope_type(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="test",
            message="msg",
            scope_type="invalid",
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert "scope_type" not in events[0]["data"]

    @pytest.mark.asyncio
    async def test_empty_scope_id_normalized_to_none(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="test",
            message="msg",
            scope_id="   ",
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert "scope_id" not in events[0]["data"]

    @pytest.mark.asyncio
    async def test_memory_payload_forwarded(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="memory",
            message="hits",
            memory={"count": 3},
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert events[0]["data"]["memory"] == {"count": 3}

    @pytest.mark.asyncio
    async def test_empty_memory_not_forwarded(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="test",
            message="msg",
            memory={},
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert "memory" not in events[0]["data"]

    @pytest.mark.asyncio
    async def test_redaction_payload_forwarded(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_enrichment(
            phase="redaction",
            message="redacted",
            redaction={"fields": ["ssn"]},
        )
        await _drain()
        events = _events_of_type(bridge, "enrichment")
        assert events[0]["data"]["redaction"] == {"fields": ["ssn"]}


# MARK: System Tool Progress


class TestReportSystemToolProgress:
    @pytest.mark.asyncio
    async def test_emits_delta_chunks(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_tool_start(
            tool_name="web_search",
            event_id="st-1",
            tool_type="system",
        )
        await _drain()

        reporter.report_system_tool_progress(
            event_id="st-1",
            tool_name="web_search",
            chunk_count=1,
            elapsed_seconds=0.1,
            text="Hello",
        )
        await _drain()

        reporter.report_system_tool_progress(
            event_id="st-1",
            tool_name="web_search",
            chunk_count=2,
            elapsed_seconds=0.2,
            text="Hello World",
        )
        await _drain()

        chunks = _events_of_type(bridge, "system_tool_chunk")
        assert len(chunks) == 2
        assert chunks[0]["data"]["text"] == "Hello"
        assert chunks[1]["data"]["text"] == " World"

    @pytest.mark.asyncio
    async def test_no_delta_emitted_for_duplicate(self) -> None:
        bridge, reporter = _make_pair()
        reporter._stream_text_by_tool_id["st-2"] = ""

        reporter.report_system_tool_progress(
            event_id="st-2",
            tool_name="search",
            chunk_count=1,
            elapsed_seconds=0.1,
            text="Hello",
        )
        await _drain()

        reporter.report_system_tool_progress(
            event_id="st-2",
            tool_name="search",
            chunk_count=2,
            elapsed_seconds=0.2,
            text="Hello",
        )
        await _drain()

        chunks = _events_of_type(bridge, "system_tool_chunk")
        assert len(chunks) == 1

    @pytest.mark.asyncio
    async def test_contract_stream_mode_skips_system_tool_progress_state_updates(self) -> None:
        bridge, reporter = _make_pair()
        reporter._stream_text_by_tool_id["st-3"] = "existing"
        token = current_sdk_delivery_mode.set("stream")
        try:
            reporter.report_system_tool_progress(
                event_id="st-3",
                tool_name="search",
                chunk_count=1,
                elapsed_seconds=0.1,
                text="updated",
            )
        finally:
            current_sdk_delivery_mode.reset(token)
        await _drain()

        assert reporter._stream_text_by_tool_id["st-3"] == "existing"
        chunks = _events_of_type(bridge, "system_tool_chunk")
        assert chunks == []


# MARK: Status Message


class TestReportStatusMessage:
    @pytest.mark.asyncio
    async def test_forwards_status(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_status_message("Starting phase 2", assistant_id="orchestrator")
        await _drain()
        events = _events_of_type(bridge, "status_message")
        assert len(events) == 1
        assert events[0]["data"]["message"] == "Starting phase 2"
        assert events[0]["data"]["assistant_id"] == "orchestrator"

    @pytest.mark.asyncio
    async def test_defaults_assistant_id(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_status_message("msg", assistant_id=None)
        await _drain()
        events = _events_of_type(bridge, "status_message")
        assert events[0]["data"]["assistant_id"] == "assistant"

    @pytest.mark.asyncio
    async def test_strips_whitespace_assistant_id(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_status_message("msg", assistant_id="   ")
        await _drain()
        events = _events_of_type(bridge, "status_message")
        assert events[0]["data"]["assistant_id"] == "assistant"


# MARK: Response Chunk


class TestReportResponseChunk:
    @pytest.mark.asyncio
    async def test_full_text_delta(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_response_chunk("A", assistant_id="a1", full_text="A")
        await _drain()
        reporter.report_response_chunk("AB", assistant_id="a1", full_text="AB")
        await _drain()
        chunks = _events_of_type(bridge, "assistant_chunk")
        assert [c["data"]["text"] for c in chunks] == ["A", "B"]

    @pytest.mark.asyncio
    async def test_delta_text_without_full_text(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_response_chunk("chunk1", assistant_id="a1")
        await _drain()
        reporter.report_response_chunk("chunk2", assistant_id="a1")
        await _drain()
        chunks = _events_of_type(bridge, "assistant_chunk")
        assert [c["data"]["text"] for c in chunks] == ["chunk1", "chunk2"]

    @pytest.mark.asyncio
    async def test_empty_delta_not_emitted(self) -> None:
        bridge, reporter = _make_pair()
        reporter.report_response_chunk("", assistant_id="a1")
        await _drain()
        chunks = _events_of_type(bridge, "assistant_chunk")
        assert len(chunks) == 0

    @pytest.mark.asyncio
    async def test_contract_stream_mode_skips_response_chunk_state_updates(self) -> None:
        bridge, reporter = _make_pair()
        reporter._response_stream_text_by_assistant_id["a1"] = "existing"
        token = current_sdk_delivery_mode.set("stream")
        try:
            reporter.report_response_chunk("new", assistant_id="a1", full_text="existingnew")
        finally:
            current_sdk_delivery_mode.reset(token)
        await _drain()

        assert reporter._response_stream_text_by_assistant_id["a1"] == "existing"
        chunks = _events_of_type(bridge, "assistant_chunk")
        assert chunks == []


# MARK: _compute_stream_delta


class TestComputeStreamDelta:
    def test_empty_incoming(self) -> None:
        assert StudioReporter._compute_stream_delta("abc", "") == ""

    def test_empty_previous(self) -> None:
        assert StudioReporter._compute_stream_delta("", "hello") == "hello"

    def test_incoming_extends_previous(self) -> None:
        assert StudioReporter._compute_stream_delta("Hello", "Hello World") == " World"

    def test_previous_extends_incoming(self) -> None:
        assert StudioReporter._compute_stream_delta("Hello World", "Hello") == ""

    def test_diverged_text(self) -> None:
        result = StudioReporter._compute_stream_delta("ABC", "ABX")
        assert result == "X"

    def test_completely_different(self) -> None:
        result = StudioReporter._compute_stream_delta("abc", "XYZ")
        assert result == "XYZ"

    def test_both_empty(self) -> None:
        assert StudioReporter._compute_stream_delta("", "") == ""


# MARK: _submit with closed loop


class TestSubmitClosedLoop:
    @pytest.mark.asyncio
    async def test_handles_closed_loop(self, recwarn: pytest.WarningsRecorder) -> None:
        bridge = EventBridge("closed-test")
        loop = asyncio.new_event_loop()
        loop.close()
        reporter = StudioReporter(bridge=bridge, loop=loop)
        reporter.report_phase_change("planning")
        gc.collect()
        assert bridge.get_history() == []
        assert not any(
            issubclass(warning.category, RuntimeWarning)
            and "was never awaited" in str(warning.message)
            for warning in recwarn
        )


# MARK: Flush


class TestFlush:
    @pytest.mark.asyncio
    async def test_flush_waits_for_pending_bridge_submissions(self) -> None:
        bridge, reporter = _make_pair()
        original_emit = bridge.emit

        async def delayed_emit(event_type: str, data: dict[str, Any]) -> None:
            await asyncio.sleep(0.02)
            await original_emit(event_type, data)

        bridge.emit = delayed_emit  # type: ignore[method-assign]

        reporter.report_tool_start(
            tool_name="fetch_data",
            event_id="tool-1",
            tool_type="func",
            agent_name="Research Coordinator",
        )

        assert bridge.get_history() == []

        await reporter.flush()

        events = _events_of_type(bridge, "tool_event")
        assert len(events) == 1
        assert events[0]["data"]["tool_name"] == "fetch_data"
