# pyright: strict
"""Shared state contract for the Studio reporter mixins.

:class:`StudioReporter` is assembled from several mixins (input, tools,
phases, submission, display stubs). Each mixin reaches into the same set of
instance attributes that :class:`StudioReporter.__init__` populates. Declaring
those attributes once here — instead of redeclaring an overlapping ``Any``
subset in every mixin — gives all mixins a single, agreed-on typed view of the
reporter's mutable state and lets pyright typecheck each mixin in isolation.

The contract is an abstract base: the attributes are *declared* here (not
initialized), and ``StudioReporter`` owns their initialization. Mixins inherit
this base so each one typechecks on its own while agreeing on the attribute
types; ``session_id`` and ``_submit`` are abstract so the concrete reporter
must supply them.
"""

from __future__ import annotations

import asyncio
import threading
from abc import ABC, abstractmethod
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any

from ...event_bridge import EventBridge

# MARK: Reporter State Contract


class ReporterState(ABC):
    """Typed declaration of the mutable state shared across reporter mixins."""

    # Event bridge the reporter forwards SDK callbacks onto.
    _bridge: EventBridge
    # Worker→loop hop for dispatching bridge coroutines off-thread.
    _loop: asyncio.AbstractEventLoop
    # In-flight bridge submissions, drained by ``flush()`` before terminal events.
    _pending_submissions: set[Future[None]]
    _pending_submissions_lock: threading.Lock

    # Maps tool_id -> (tool_type, tool_name, agent_name, swarm_name).
    _tool_types: dict[str, tuple[str, str, str | None, str | None]]
    # Tracks full streaming text per system tool to emit deltas to the UI.
    stream_text_by_tool_id: dict[str, str]
    # Tracks streamed assistant text by source to emit stable deltas.
    response_stream_text_by_assistant_id: dict[str, str]

    # Current tool context for interrupt attribution.
    _current_tool_name: str | None
    # Per-turn interrupt id scaffolding.
    _turn_id: str
    _interrupt_counter: int
    # One-shot flag: the next streamed chunk overwrites the UI bubble.
    _next_response_chunk_replaces: bool

    @property
    @abstractmethod
    def session_id(self) -> str:
        """Session id, provided by :class:`StudioReporter` from its bridge."""

    @abstractmethod
    def _submit(self, coro: Coroutine[Any, Any, None]) -> None:
        """Dispatch a bridge coroutine onto the reporter's event loop."""


__all__ = ["ReporterState"]
