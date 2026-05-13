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
  onto the asyncio loop in a single hop per chunk (see ``_replay_normalized_events``).
"""

from __future__ import annotations

import asyncio
from typing import Any

from maivn.events import NormalizedEventForwardingState, forward_normalized_event

# MARK: Replay Ownership

# Event names whose stream-replay copies are forwarded back through the
# reporter (e.g. so chunked text events round-trip the same way invoke-mode
# events do). Public so tests can assert the explicit routing contract.
REPORTER_REPLAY_EVENT_NAMES = frozenset(
    {
        "assistant_chunk",
        "system_tool_chunk",
    }
)
# Event names whose stream-replay copies are forwarded back through the
# EventBridge (instead of the reporter). Public for the same reason.
BRIDGE_REPLAY_EVENT_NAMES = frozenset({"interrupt_required"})


def should_replay_event_to_reporter(event_name: str) -> bool:
    return event_name in REPORTER_REPLAY_EVENT_NAMES


def should_replay_event_to_bridge(event_name: str) -> bool:
    return event_name in BRIDGE_REPLAY_EVENT_NAMES


# MARK: Forwarding


async def _forward_normalized_replay_event(
    normalized_event: Any,
    *,
    reporter: Any | None,
    bridge: Any | None,
    state: NormalizedEventForwardingState,
) -> None:
    from ...studio_reporter.reporter import normalized_stream_replay_context

    with normalized_stream_replay_context():
        await forward_normalized_event(
            normalized_event,
            reporter=reporter,
            bridge=bridge,
            state=state,
        )


async def _forward_normalized_replay_batch(
    batch: list[tuple[Any, Any | None, Any | None]],
    *,
    state: NormalizedEventForwardingState,
) -> None:
    """Forward a pre-filtered batch of replay events sequentially on one loop hop."""
    from ...studio_reporter.reporter import normalized_stream_replay_context

    with normalized_stream_replay_context():
        for normalized_event, replay_reporter, replay_bridge in batch:
            await forward_normalized_event(
                normalized_event,
                reporter=replay_reporter,
                bridge=replay_bridge,
                state=state,
            )


def _replay_normalized_events(
    normalized_events: list[Any],
    *,
    reporter: Any,
    bridge: Any | None,
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
    single coroutine — one cross-thread hop per chunk, regardless of how many
    events the SDK produced for that chunk.
    """
    batch: list[tuple[Any, Any | None, Any | None]] = []
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
    future.result()


__all__ = [
    "BRIDGE_REPLAY_EVENT_NAMES",
    "REPORTER_REPLAY_EVENT_NAMES",
    "_forward_normalized_replay_batch",
    "_forward_normalized_replay_event",
    "_replay_normalized_events",
    "should_replay_event_to_bridge",
    "should_replay_event_to_reporter",
]
