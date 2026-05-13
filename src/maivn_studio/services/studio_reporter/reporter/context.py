"""Contract-stream replay context for the Studio reporter.

In stream mode the SDK delivers normalized events via a replay loop instead
of through the reporter. The reporter suppresses ``report_response_chunk`` /
``print_final_response`` to avoid duplicate UI chunks — but the replay loop
itself needs to be exempt so its chunks still flow.

Setting :data:`_normalized_stream_replay_active` to ``True`` is the opt-out
signal. Scheduled fires use :func:`activate_normalized_stream_replay` because
they don't run the chat-session replay loop; chat sessions use the
:func:`normalized_stream_replay_context` context manager around the loop body.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_normalized_stream_replay_active: ContextVar[bool] = ContextVar(
    "studio_normalized_stream_replay_active",
    default=False,
)


@contextmanager
def normalized_stream_replay_context() -> Iterator[None]:
    """Allow normalized replay chunks through contract-stream suppression."""
    token = _normalized_stream_replay_active.set(True)
    try:
        yield
    finally:
        _normalized_stream_replay_active.reset(token)


def activate_normalized_stream_replay() -> None:
    """Set the replay-active contextvar without a paired reset.

    Use this from sync callbacks (e.g. scheduled-job ``on_fire``) that own the
    rest of an asyncio Task's lifetime. The contextvar stays set for the rest
    of the task and is dropped when the task completes — there's no shared
    context to leak into.
    """
    _normalized_stream_replay_active.set(True)


__all__ = [
    "_normalized_stream_replay_active",
    "activate_normalized_stream_replay",
    "normalized_stream_replay_context",
]
