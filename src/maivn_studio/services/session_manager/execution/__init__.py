"""Session execution package.

Public surface (used by ``manager.py`` and tests):

- :func:`execute_session` - main turn loop entry point
- :func:`flush_reporter_events` - reporter flush helper
- :func:`supports_structured_output_kwarg` - capability probe
- :func:`wait_for_event_subscriber` - subscriber-wait helper (tested directly)
- :func:`should_replay_event_to_reporter` / :func:`should_replay_event_to_bridge`
  and :func:`replay_normalized_events` (tested directly)
- :data:`FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS` - wait timeout constant (tested)
"""

# pyright: strict
from __future__ import annotations

from .batch import BatchInputSpec, BatchTurnResult
from .capabilities import (
    FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS,
    build_stream_tool_contract_maps,
    flush_reporter_events,
    supports_structured_output_kwarg,
    wait_for_event_subscriber,
)
from .replay import (
    BRIDGE_REPLAY_EVENT_NAMES,
    REPORTER_REPLAY_EVENT_NAMES,
    replay_normalized_events,
    should_replay_event_to_bridge,
    should_replay_event_to_reporter,
)
from .session import execute_session

__all__ = [
    "BRIDGE_REPLAY_EVENT_NAMES",
    "FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS",
    "REPORTER_REPLAY_EVENT_NAMES",
    "BatchInputSpec",
    "BatchTurnResult",
    "build_stream_tool_contract_maps",
    "execute_session",
    "flush_reporter_events",
    "replay_normalized_events",
    "should_replay_event_to_bridge",
    "should_replay_event_to_reporter",
    "supports_structured_output_kwarg",
    "wait_for_event_subscriber",
]
