"""Stream-mode normalized event replay routing.

In stream mode, the SDK emits SSE events that Studio normalizes back into
``AppEvent`` objects. Most of those events are already delivered to the
frontend through the reporter; a small set need to be re-delivered through
either the reporter or the bridge so the studio UI sees the same shape it
would in invoke mode.

This module owns:

- the explicit allow-lists for which event names round-trip back through which
  surface (reporter vs. bridge), and
- the cross-thread plumbing that ferries a chunk's worth of normalized events
  onto the asyncio loop in a single hop per chunk (see
  :func:`replay_normalized_events`).
"""

# pyright: strict
from __future__ import annotations

import asyncio

from maivn.events import (
    AppEvent,
    EventBridge,
    NormalizedEventForwardingState,
    forward_normalized_event,
)

# MARK: Replay Ownership

# Event names whose stream-replay copies are forwarded back through the
# reporter (e.g. so chunked text events round-trip the same way invoke-mode
# events do). Public so tests can assert the explicit routing contract.
REPORTER_REPLAY_EVENT_NAMES: frozenset[str] = frozenset(
    {
        "assistant_chunk",
        "system_tool_chunk",
    }
)
# Event names whose stream-replay copies are forwarded back through the
# EventBridge (instead of the reporter). Public for the same reason.
BRIDGE_REPLAY_EVENT_NAMES: frozenset[str] = frozenset({"interrupt_required"})


def should_replay_event_to_reporter(event_name: str) -> bool:
    return event_name in REPORTER_REPLAY_EVENT_NAMES


def should_replay_event_to_bridge(event_name: str) -> bool:
    return event_name in BRIDGE_REPLAY_EVENT_NAMES


# MARK: Forwarding

# A single replay batch entry: the normalized event plus the surfaces it should
# be forwarded through (reporter, bridge); either may be None to skip.
ReplayBatchEntry = tuple[AppEvent, object | None, EventBridge | None]


async def _forward_normalized_replay_batch(
    batch: list[ReplayBatchEntry],
    *,
    state: NormalizedEventForwardingState,
) -> None:
    """Forward a pre-filtered batch of replay events sequentially on one loop hop."""
    from ...studio_reporter.reporter import normalized_stream_replay_context

    with normalized_stream_replay_context():
        for normalized_event, replay_reporter, replay_bridge in batch:
            _ = await forward_normalized_event(
                normalized_event,
                reporter=replay_reporter,
                bridge=replay_bridge,
                state=state,
            )


def replay_normalized_events(
    normalized_events: list[AppEvent],
    *,
    reporter: object,
    bridge: EventBridge | None,
    loop: asyncio.AbstractEventLoop,
    forwarding_state: NormalizedEventForwardingState,
) -> None:
    """Replay normalized events back through the reporter / bridge.

    Each stream chunk yields a list of normalized events. Forwarding each one
    via its own ``run_coroutine_threadsafe(...) + future.result()`` round-trip
    serializes the worker thread against the asyncio loop for every event,
    which dominates the per-chunk cost for streaming turns with many small
    ``assistant_chunk`` / ``system_tool_chunk`` events.

    Instead we filter the batch up front and ship the survivors through a
    single coroutine - one cross-thread hop per chunk, regardless of how many
    events the SDK produced for that chunk.
    """
    batch: list[ReplayBatchEntry] = []
    for normalized_event in normalized_events:
        replay_reporter = (
            reporter if should_replay_event_to_reporter(normalized_event.event_name) else None
        )
        replay_bridge = (
            bridge if should_replay_event_to_bridge(normalized_event.event_name) else None
        )
        if replay_reporter is None and replay_bridge is None:
            continue
        batch.append((normalized_event, replay_reporter, replay_bridge))

    if not batch:
        return

    future = asyncio.run_coroutine_threadsafe(
        _forward_normalized_replay_batch(batch, state=forwarding_state),
        loop,
    )
    _ = future.result()


__all__ = [
    "BRIDGE_REPLAY_EVENT_NAMES",
    "REPORTER_REPLAY_EVENT_NAMES",
    "replay_normalized_events",
    "should_replay_event_to_bridge",
    "should_replay_event_to_reporter",
]
