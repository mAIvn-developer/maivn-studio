# pyright: strict
"""Bridge submission management — :meth:`flush` and the worker→loop hop.

Studio dispatches reporter callbacks from worker threads via
``asyncio.run_coroutine_threadsafe``. This mixin owns the bookkeeping that
makes those submissions awaitable as a group, so terminal events
(``turn_complete`` / ``error``) can be ordered after the bridge has actually
drained the preceding tool/agent events.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC
from collections.abc import Coroutine
from concurrent.futures import Future
from typing import Any

from typing_extensions import override

from .state import ReporterState

logger = logging.getLogger("maivn_studio.services.studio_reporter.reporter")


# MARK: Submission Mixin


class SubmissionMixin(ReporterState, ABC):
    """Manage cross-thread coroutine submissions and group-flush semantics."""

    async def flush(self) -> None:
        """Wait for in-flight bridge submissions to finish.

        Studio dispatches reporter events from worker threads via
        ``run_coroutine_threadsafe``. Without draining those futures before
        emitting ``turn_complete`` / ``error``, terminal events can overtake
        tool and agent events on the bridge.
        """
        if self._loop.is_closed():
            return

        while True:
            with self._pending_submissions_lock:
                pending = tuple(self._pending_submissions)

            if not pending:
                return

            results = await asyncio.gather(
                *(asyncio.wrap_future(future) for future in pending),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(
                        "[STUDIO_REPORTER] Bridge submission failed during flush: %s",
                        result,
                    )

    @override
    def _submit(self, coro: Coroutine[Any, Any, None]) -> None:
        if self._loop.is_closed():
            logger.warning("[STUDIO_REPORTER] Event loop is closed, cannot submit event")
            coro.close()
            return
        logger.debug("[STUDIO_REPORTER] Submitting event to bridge")
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError as exc:
            coro.close()
            logger.warning("[STUDIO_REPORTER] Bridge submission failed: %s", exc)
            return

        with self._pending_submissions_lock:
            self._pending_submissions.add(future)

        def _cleanup_submission(done_future: Future[None]) -> None:
            with self._pending_submissions_lock:
                self._pending_submissions.discard(done_future)

            try:
                _ = done_future.result()
            except Exception as exc:  # noqa: BLE001 - log + drop; submissions are best-effort
                logger.warning("[STUDIO_REPORTER] Bridge submission failed: %s", exc)

        future.add_done_callback(_cleanup_submission)


__all__ = ["SubmissionMixin"]
