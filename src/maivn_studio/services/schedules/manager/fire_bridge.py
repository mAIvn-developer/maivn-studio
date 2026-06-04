"""Per-fire event bridge wiring — on_fire / on_success / on_error / on_skip closures.

These are pulled out of :class:`ScheduleManager` because each fire's lifecycle
needs four cooperating callbacks (~200 LOC) that all close over the same
``job`` / ``app_id`` / ``config`` / ``manager`` and would otherwise dominate
the manager class.
"""

# pyright: strict

from __future__ import annotations

import asyncio
import logging
import threading
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Protocol, cast

from maivn import RunRecord, ScheduledJob
from maivn._internal.utils.reporting.context import (
    current_reporter,
    current_sdk_delivery_mode,
)
from maivn.messages import HumanMessage

from maivn_studio.services.event_bridge import create_event_bridge, get_event_bridge
from maivn_studio.services.studio_reporter.reporter import (
    StudioReporter,
    activate_normalized_stream_replay,
)

from ..models import ScheduleConfig
from .ids import fire_event_session_id, predict_next_run_iso
from .serialization import build_terminal_event_data, duration_ms

logger = logging.getLogger(__name__)


# MARK: Manager seam


class ScheduleManagerLike(Protocol):
    """Minimal :class:`ScheduleManager` surface the fire callbacks reach back into.

    Typing the seam with a Protocol (instead of importing the concrete
    ``ScheduleManager``) keeps ``fire_bridge`` free of a back-import on
    ``core`` — ``core`` imports ``wire_fire_event_bridge`` at runtime, so a
    reverse import would form a module cycle.
    """

    lock: threading.Lock
    active_runs_by_app: dict[str, dict[str, RunRecord]]
    fire_session_ids_by_app: dict[str, list[str]]

    def emit_app_event(
        self,
        app_id: str,
        event_name: str,
        data: dict[str, object],
        loop: asyncio.AbstractEventLoop,
    ) -> None: ...


# The SDK stores ``BaseReporter | None`` in this context var; narrow it to the
# concrete StudioReporter we set so callers see the precise type.
_current_reporter: ContextVar[StudioReporter | None] = cast(
    "ContextVar[StudioReporter | None]", current_reporter
)


# MARK: Fire bridge wiring


def wire_fire_event_bridge(
    manager: ScheduleManagerLike,
    job: ScheduledJob,
    app_id: str,
    config: ScheduleConfig,
    prompt_messages: list[HumanMessage],
) -> None:
    """Bind a per-fire EventBridge + reporter so the executor's events stream
    through SSE the same way a chat session would. This is what makes each
    scheduled run renderable as a full chat exchange in the UI.

    The contextvar is set inside ``on_fire``, which runs in the same asyncio
    Task as the runner's ``await _invoke_method()``. ContextVars set inside
    the same Task persist for the rest of that Task, so the executor invoke
    sees the reporter we bind here.
    """
    method = config.method
    # Used by maivn's reporter delivery dispatch — chat sessions set this
    # too. ``stream``-family methods need ``stream`` so live token deltas
    # forward through the bridge.
    delivery_mode = "stream" if method in {"stream", "astream"} else "invoke"

    # ``HumanMessage.content`` is ``str | list[...]`` whose list arm carries
    # langchain's partially-unstubbed ``dict`` element; cast to object so the
    # str-coercion below stays type-clean. Schedule prompts are always plain
    # text, so non-string content collapses to "".
    first_content: object = cast("object", prompt_messages[0].content) if prompt_messages else ""
    prompt_text = first_content if isinstance(first_content, str) else ""

    def _on_fire(record: RunRecord) -> None:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            logger.warning(
                "Schedule fire %s: no running loop; cannot bind event bridge",
                record.fire_id,
            )
            return

        # Log every fire (manual + cron) so we can correlate the on-disk
        # job count with what the UI reports. Excessive fires for a single
        # cron tick will show up here as multiple entries with the same
        # ``scheduled_at``.
        logger.info(
            "Schedule fire %s: app=%s job=%s scheduled_at=%s manual=%s",
            record.fire_id,
            app_id,
            job.id,
            record.scheduled_at.isoformat(),
            record.metadata.get("manual", False),
        )

        event_session_id = fire_event_session_id(job.id, record.fire_id)
        record.metadata["event_session_id"] = event_session_id
        # Tag with job_id so _summarize can drop active runs that belong
        # to a previous job (its on_fire still mutates this shared map).
        record.metadata["job_id"] = job.id

        with manager.lock:
            manager.active_runs_by_app.setdefault(app_id, {})[record.fire_id] = record
            session_ids = manager.fire_session_ids_by_app.setdefault(app_id, [])
            if event_session_id not in session_ids:
                session_ids.append(event_session_id)

        bridge = get_event_bridge(event_session_id)
        if bridge is None:
            bridge = create_event_bridge(event_session_id)
        elif bridge.stream_is_closed:
            bridge.reopen()

        reporter = StudioReporter(bridge, loop)

        # ContextVars set in this callback persist for the rest of the
        # runner Task, so the upcoming executor invoke picks up the
        # reporter and delivery mode.
        _ = _current_reporter.set(reporter)
        _ = current_sdk_delivery_mode.set(delivery_mode)
        # In stream mode, StudioReporter normally suppresses
        # ``report_response_chunk`` / ``print_final_response`` because chat
        # sessions replay normalized events themselves. Schedules don't run
        # that replay loop, so we mark the task as already inside replay
        # context — the reporter then forwards the orchestrator's chunks
        # straight to the bridge.
        if delivery_mode == "stream":
            activate_normalized_stream_replay()

        # Mirror the chat panel's session_start event so the frontend's
        # existing event handlers light up phase chips, tool cards, etc.
        session_start: dict[str, object] = {
            "session_id": event_session_id,
            "app_id": app_id,
            "schedule_job_id": job.id,
            "schedule_fire_id": record.fire_id,
            "scheduled_at": record.scheduled_at.isoformat(),
            "fired_at": (record.fired_at.isoformat() if record.fired_at else None),
            "attempt": record.attempt,
            "method": method,
            "prompt": prompt_text,
            "origin": "schedule",
        }
        _ = asyncio.run_coroutine_threadsafe(
            bridge.emit("session_start", session_start),
            loop,
        )

        # Push to the per-app activity bridge so the frontend renders
        # the run card the instant the fire starts. The event carries
        # event_session_id so the chat-style stream at
        # /fires/{fire_id}/events can be opened immediately, and
        # next_run_at so the upcoming-card countdown rolls over to the
        # next tick without waiting for a poll.
        manager.emit_app_event(
            app_id,
            "schedule_fire_started",
            {
                "app_id": app_id,
                "fire_id": record.fire_id,
                "event_session_id": event_session_id,
                "scheduled_at": record.scheduled_at.isoformat(),
                "fired_at": record.fired_at.isoformat() if record.fired_at else None,
                "attempt": record.attempt,
                "next_run_at": predict_next_run_iso(job, record.scheduled_at),
            },
            loop,
        )

    def _on_terminal(record: RunRecord, *, terminal: str) -> None:
        with manager.lock:
            _ = manager.active_runs_by_app.get(app_id, {}).pop(record.fire_id, None)

        event_session_id = record.metadata.get("event_session_id") if record.metadata else None
        if not isinstance(event_session_id, str):
            return
        bridge = get_event_bridge(event_session_id)
        if bridge is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return

        _ = asyncio.run_coroutine_threadsafe(
            bridge.emit(
                "turn_complete" if terminal == "success" else "error",
                build_terminal_event_data(
                    session_id=event_session_id,
                    schedule_fire_id=record.fire_id,
                    status=record.status,
                    duration_ms=duration_ms(record),
                    error=str(record.error) if record.error else None,
                    result=record.result,
                ),
            ),
            loop,
        )

        # Push to the per-app bridge so the frontend flips the card's
        # status pill from running -> succeeded/failed without waiting
        # for the next reconciliation poll.
        manager.emit_app_event(
            app_id,
            "schedule_fire_completed",
            {
                "app_id": app_id,
                "fire_id": record.fire_id,
                "status": record.status,
                "finished_at": (record.finished_at.isoformat() if record.finished_at else None),
                "error": str(record.error) if record.error else None,
                "duration_ms": duration_ms(record),
                # Computed from now (not the fire's scheduled time) so a
                # long-running fire that overran one or more cron ticks
                # reports the actual next future tick, not one already
                # in the past.
                "next_run_at": predict_next_run_iso(
                    job,
                    record.finished_at or datetime.now(tz=timezone.utc),
                ),
            },
            loop,
        )

        # Bridge stays in the registry so a card that subscribes after
        # the fire completes still gets to replay history. Cleanup
        # happens when the schedule itself is stopped or removed.

    # Skipped fires (overlap / jitter / misfire) never trigger on_fire,
    # so on_skip just removes any stale active record for parity. We
    # still push to the per-app bridge so the UI's skipped-runs counter
    # updates without waiting for a reconciliation poll.
    def _on_skip(record: RunRecord) -> None:
        with manager.lock:
            _ = manager.active_runs_by_app.get(app_id, {}).pop(record.fire_id, None)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        manager.emit_app_event(
            app_id,
            "schedule_fire_skipped",
            {
                "app_id": app_id,
                "fire_id": record.fire_id,
                "status": record.status,
                "scheduled_at": record.scheduled_at.isoformat(),
                "next_run_at": predict_next_run_iso(job, record.scheduled_at),
            },
            loop,
        )

    def _on_terminal_success(record: RunRecord) -> None:
        _on_terminal(record, terminal="success")

    def _on_terminal_error(record: RunRecord) -> None:
        _on_terminal(record, terminal="error")

    _ = job.on_fire(_on_fire)
    _ = job.on_success(_on_terminal_success)
    _ = job.on_error(_on_terminal_error)
    _ = job.on_skip(_on_skip)


__all__ = ["wire_fire_event_bridge"]
