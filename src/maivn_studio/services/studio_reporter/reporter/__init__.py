# pyright: strict
"""Studio reporter package.

Re-exports the public surface of the reporter so existing imports — including
the interrupt helpers that tests monkey-patch on this module — keep working:

- :class:`StudioReporter`
- :func:`normalized_stream_replay_context` / :func:`activate_normalized_stream_replay`
- :func:`register_interrupt` / :func:`get_interrupt_response` /
  :func:`cleanup_interrupt` — re-exported so existing tests can still
  ``patch("maivn_studio.services.studio_reporter.reporter.register_interrupt", ...)``
  and hit the seam the reporter actually uses.
"""

from __future__ import annotations

from ..interrupts import cleanup_interrupt, get_interrupt_response, register_interrupt
from .context import (
    activate_normalized_stream_replay,
    normalized_stream_replay_active,
    normalized_stream_replay_context,
)
from .core import StudioReporter

__all__ = [
    "StudioReporter",
    "activate_normalized_stream_replay",
    "cleanup_interrupt",
    "get_interrupt_response",
    "normalized_stream_replay_active",
    "normalized_stream_replay_context",
    "register_interrupt",
]
