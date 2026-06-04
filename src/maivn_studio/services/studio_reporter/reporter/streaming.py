# pyright: strict
"""Streaming-mode helpers: append-only delta computation + delivery-mode check."""

from __future__ import annotations

from maivn._internal.utils.reporting.context import (
    current_sdk_delivery_mode,
)

from .context import normalized_stream_replay_active

# MARK: Delta Computation


def compute_stream_delta(previous: str, incoming: str) -> str:
    """Compute append-only deltas from cumulative snapshots.

    The SDK emits each stream chunk as the full cumulative text. The reporter
    converts those to deltas before pushing onto the bridge so the UI only
    receives the new fragment per chunk, never the entire prefix every time.

    - Common-prefix case: ``incoming.startswith(previous)`` → return suffix.
    - Re-entrant duplicate: ``previous.startswith(incoming)`` → no new text.
    - Divergent: walk the common prefix, return what's after it.
    """
    if not incoming:
        return ""
    if not previous:
        return incoming
    if incoming.startswith(previous):
        return incoming[len(previous) :]
    if previous.startswith(incoming):
        return ""

    max_len = min(len(previous), len(incoming))
    shared = 0
    while shared < max_len and previous[shared] == incoming[shared]:
        shared += 1
    if shared == 0:
        return incoming
    return incoming[shared:]


# MARK: Delivery Mode


def is_contract_stream_mode() -> bool:
    """Return ``True`` when we're delivering through the SDK's contract stream.

    Contract stream mode means stream-mode events are flowing through the
    normalized replay loop in :mod:`session_manager.execution.replay`, so the
    reporter must suppress its own response/chunk delivery to avoid emitting
    the same chunk twice. Replay code marks itself with the
    ``normalized_stream_replay_active`` contextvar to opt out of suppression.
    """
    return current_sdk_delivery_mode.get() == "stream" and not (
        normalized_stream_replay_active.get()
    )


__all__ = [
    "compute_stream_delta",
    "is_contract_stream_mode",
]
