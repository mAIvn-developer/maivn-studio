# pyright: strict
"""Studio reporter that forwards SDK events to the UI event bridge."""

from __future__ import annotations

import asyncio
import threading
import uuid
from typing import final

from maivn._internal.utils.reporting.terminal_reporter import (
    BaseReporter,
)
from typing_extensions import override

from ...event_bridge import EventBridge
from .display_stubs import DisplayStubsMixin
from .input import InputMixin
from .phases import PhaseReportingMixin
from .state import ReporterState
from .submission import SubmissionMixin
from .tools import ToolReportingMixin

# MARK: Reporter


@final
class StudioReporter(
    InputMixin,
    ToolReportingMixin,
    PhaseReportingMixin,
    DisplayStubsMixin,
    SubmissionMixin,
    ReporterState,
    BaseReporter,
):
    """Lightweight reporter that pushes SDK callbacks into the Studio bridge.

    Replay ownership and bridge-level identity handling live upstream in the
    session execution path and shared ``maivn.events.EventBridge`` contract.
    This reporter stays intentionally thin and forwards only the SDK callbacks
    raised during the active turn.
    """

    def __init__(self, bridge: EventBridge, loop: asyncio.AbstractEventLoop) -> None:
        super().__init__()
        self._bridge = bridge
        self._loop = loop
        # Maps tool_id -> (tool_type, tool_name, agent_name, swarm_name)
        self._tool_types = {}
        # Tracks full streaming text per system tool to emit deltas to the UI.
        self.stream_text_by_tool_id = {}
        # Tracks streamed assistant text by source to emit stable deltas.
        self.response_stream_text_by_assistant_id = {}
        # Track current tool context for interrupts
        self._current_tool_name = None
        self._interrupt_counter = 0
        # Unique suffix per reporter instance so interrupt IDs don't collide
        # across turns (each turn creates a fresh StudioReporter).
        self._turn_id = uuid.uuid4().hex[:8]
        # One-shot flag set by ``report_enrichment`` on reevaluate so the next
        # streamed chunk overwrites the UI bubble instead of appending.
        self._next_response_chunk_replaces = False
        # Track bridge submissions so callers can wait for UI events to land
        # before emitting terminal turn/session events.
        self._pending_submissions = set()
        self._pending_submissions_lock = threading.Lock()

    @property
    @override
    def session_id(self) -> str:
        """Get session ID from bridge."""
        return self._bridge.session_id


__all__ = ["StudioReporter"]
