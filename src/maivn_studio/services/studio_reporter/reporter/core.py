"""Studio reporter that forwards SDK events to the UI event bridge."""

from __future__ import annotations

import asyncio
import threading
import uuid
from concurrent.futures import Future
from typing import Any

from maivn._internal.utils.reporting.terminal_reporter import BaseReporter

from ...event_bridge import EventBridge
from .display_stubs import DisplayStubsMixin
from .input import InputMixin
from .phases import PhaseReportingMixin
from .streaming import compute_stream_delta, is_contract_stream_mode
from .submission import SubmissionMixin
from .tools import ToolReportingMixin

# MARK: Reporter


class StudioReporter(
    InputMixin,
    ToolReportingMixin,
    PhaseReportingMixin,
    DisplayStubsMixin,
    SubmissionMixin,
    BaseReporter,
):
    """Lightweight reporter that pushes SDK callbacks into the Studio bridge.

    Replay ownership and bridge-level identity handling live upstream in the
    session execution path and shared ``maivn.events.EventBridge`` contract.
    This reporter stays intentionally thin and forwards only the SDK callbacks
    raised during the active turn.
    """

    # MARK: - Static seams
    #
    # Delegate to module-level helpers in ``streaming.py``. The static methods
    # stay on the class so existing tests that reach
    # ``StudioReporter._compute_stream_delta(...)`` directly keep working.
    _compute_stream_delta = staticmethod(compute_stream_delta)
    _is_contract_stream_mode = staticmethod(is_contract_stream_mode)

    def __init__(self, bridge: EventBridge, loop: asyncio.AbstractEventLoop) -> None:
        self._bridge = bridge
        self._loop = loop
        # Maps tool_id -> (tool_type, tool_name, agent_name, swarm_name)
        self._tool_types: dict[str, tuple[str, str, str | None, str | None]] = {}
        # Tracks full streaming text per system tool to emit deltas to the UI.
        self._stream_text_by_tool_id: dict[str, str] = {}
        # Tracks streamed assistant text by source to emit stable deltas.
        self._response_stream_text_by_assistant_id: dict[str, str] = {}
        # Track current tool context for interrupts
        self._current_tool_name: str | None = None
        self._interrupt_counter = 0
        # Unique suffix per reporter instance so interrupt IDs don't collide
        # across turns (each turn creates a fresh StudioReporter).
        self._turn_id = uuid.uuid4().hex[:8]
        # Track bridge submissions so callers can wait for UI events to land
        # before emitting terminal turn/session events.
        self._pending_submissions: set[Future[Any]] = set()
        self._pending_submissions_lock = threading.Lock()

    @property
    def session_id(self) -> str:
        """Get session ID from bridge."""
        return self._bridge.session_id


__all__ = ["StudioReporter"]
