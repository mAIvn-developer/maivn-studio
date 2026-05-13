"""Session execution package.

Public surface (used by ``manager.py`` and tests):

- :func:`execute_session` — main turn loop entry point
- :func:`flush_reporter_events` — reporter flush helper
- :func:`supports_structured_output_kwarg` — capability probe
- :func:`wait_for_event_subscriber` — subscriber-wait helper (tested directly)
- :func:`should_replay_event_to_reporter` / :func:`should_replay_event_to_bridge`
  and the underscore-private replay helpers (tested directly)
- :data:`_FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS` — wait timeout constant (tested)
"""

from __future__ import annotations

from .batch import BatchInputSpec, BatchTurnResult
from .capabilities import (
    _FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS,
    build_stream_tool_contract_maps,
    flush_reporter_events,
    supports_structured_output_kwarg,
    wait_for_event_subscriber,
)
from .replay import (
    BRIDGE_REPLAY_EVENT_NAMES,
    REPORTER_REPLAY_EVENT_NAMES,
    _forward_normalized_replay_batch,
    _forward_normalized_replay_event,
    _replay_normalized_events,
    should_replay_event_to_bridge,
    should_replay_event_to_reporter,
)
from .session import execute_session

__all__ = [
    "BRIDGE_REPLAY_EVENT_NAMES",
    "BatchInputSpec",
    "BatchTurnResult",
    "REPORTER_REPLAY_EVENT_NAMES",
    "_FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS",
    "_forward_normalized_replay_batch",
    "_forward_normalized_replay_event",
    "_replay_normalized_events",
    "build_stream_tool_contract_maps",
    "execute_session",
    "flush_reporter_events",
    "should_replay_event_to_bridge",
    "should_replay_event_to_reporter",
    "supports_structured_output_kwarg",
    "wait_for_event_subscriber",
]
