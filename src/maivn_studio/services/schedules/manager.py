"""Manages live ScheduledJob instances configured through Studio."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from maivn import (
    JitterSpec,
    Retry,
    RunRecord,
    ScheduledJob,
)
from maivn._internal.utils.reporting.context import (
    current_reporter,
    current_sdk_delivery_mode,
)
from maivn.messages import HumanMessage
from pydantic import BaseModel

from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.app_loader.loader import get_app_loader
from maivn_studio.services.event_bridge import (
    EventBridge,
    create_event_bridge,
    get_event_bridge,
    remove_event_bridge,
)
from maivn_studio.services.session_manager.models import (
    STUDIO_EVENT_CATEGORIES,
    latest_response_text,
)
from maivn_studio.services.studio_reporter.reporter import (
    StudioReporter,
    activate_normalized_stream_replay,
)

from .models import ScheduleConfig, ScheduleJobSummary, ScheduleRunSummary

logger = logging.getLogger(__name__)


def _fire_event_session_id(job_id: str, fire_id: str) -> str:
    """Synthetic session id for a single scheduled fire's event bridge.

    Format is intentionally distinct from real session ids so a stray lookup
    can be diagnosed in logs.
    """
    return f"schedule:{job_id}:{fire_id}"


def _app_event_bridge_id(app_id: str) -> str:
    """Synthetic session id for the per-app schedule activity push stream.

    The frontend subscribes to this once per app and learns about new fires
    the moment the SDK's on_fire callback runs — no polling required for the
    countdown -> running transition the user sees on the schedule card.
    """
    return f"schedule-app:{app_id}"


def _predict_next_run_iso(job: ScheduledJob, after: datetime) -> str | None:
    """Compute the next scheduled fire strictly after ``after`` using the
    job's schedule and return it as ISO-8601, or ``None`` if no future fire
    exists (one-shot completed, ``max_runs`` reached, etc.).

    Used to populate ``next_run_at`` in push events so the frontend's
    countdown advances the instant a fire starts/completes/skips, instead
    of waiting for the SDK's run loop to iterate plus a reconciliation
    poll. Cheap — croniter just walks the expression forward one tick.
    """
    try:
        nxt = job.schedule.next_after(after)
    except Exception:  # noqa: BLE001 — defensive; never crash the callback
        return None
    return nxt.isoformat() if nxt is not None else None


class ScheduleManager:
    """Owns the set of Studio-driven scheduled jobs, indexed by app."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs_by_app: dict[str, ScheduledJob] = {}
        self._configs_by_app: dict[str, ScheduleConfig] = {}
        # Track in-flight fires so the UI can render a card before the run
        # completes (history is only populated after _execute_run's finally
        # block). Keyed by app_id → {fire_id: RunRecord}.
        self._active_runs_by_app: dict[str, dict[str, RunRecord]] = {}
        # Track all event-session ids we've created per app so removing a
        # schedule cleans up bridges instead of leaking them.
        self._fire_session_ids_by_app: dict[str, list[str]] = {}
        # Per-app locks serialize start() calls — without this, two concurrent
        # PUT /schedules/{app} requests can both pass the existence check and
        # create separate ScheduledJob instances. Both jobs then fire on every
        # cron tick, which is what manifested as the wave of skipped_overlap
        # records when the slow first job blocked the second one's slot.
        self._app_locks: dict[str, threading.Lock] = {}

    # MARK: - Public API

    def list_jobs(self) -> list[ScheduleJobSummary]:
        with self._lock:
            return [
                self._summarize(app_id, job, self._configs_by_app[app_id])
                for app_id, job in self._jobs_by_app.items()
            ]

    def get(self, app_id: str) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_app.get(app_id)
            cfg = self._configs_by_app.get(app_id)
        if job is None or cfg is None:
            return None
        return self._summarize(app_id, job, cfg)

    def start(self, app_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
        # Per-app serialization: two concurrent PUT /schedules/{app} requests
        # would otherwise both pass the existence check, both call
        # _invoke_builder (which immediately starts the job inside the SDK's
        # _build_job), and both write a different ScheduledJob into the
        # registry. Whichever store-call lands second wins the dict slot, but
        # the loser's _bootstrap task keeps running and firing — that's what
        # produced the dozens of skipped_overlap records the user reported.
        with self._lock:
            app_lock = self._app_locks.setdefault(app_id, threading.Lock())
        with app_lock:
            return self._start_locked(app_id, config)

    def _start_locked(self, app_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
        existing = self._jobs_by_app.get(app_id)
        # Log every start request so a runaway frontend (rapid Save clicks,
        # double-submit, retry loop) is visible in the studio log alongside
        # the resulting fires.
        logger.info(
            "Schedule for app %s: start requested (replacing=%s)",
            app_id,
            existing.id if existing is not None else None,
        )
        if existing is not None and not existing.is_done:
            # ``drain=False`` so the FastAPI request thread doesn't block on
            # ``Future.result()`` — that future is bound to the same asyncio
            # loop the handler is running on, so a blocking wait deadlocks the
            # loop and stalls all other requests until the timeout fires.
            #
            # The old job's run_loop still exits (stop_event was set), and any
            # in-flight runs from it complete on their own. Their records stay
            # in the OLD job's history, so they never surface in the new
            # job's summary; the job_id filter in _summarize is what protects
            # against the brief window where an old runner's on_fire writes
            # into the shared active_runs map after we cleared it.
            existing.stop(drain=False, timeout=5)
        if existing is not None:
            self._drain_fire_bridges(app_id)

        executor = self._resolve_executor(app_id)

        # Wrap the executor with events() so each fire's invoke runs through
        # the EventRouterReporter that chat sessions rely on for tool cards,
        # assistant chunks, and agent assignments. Without this wrapper, only
        # phase-change enrichment events reach the bridge — every other UI
        # event type stays silent.
        events_factory = getattr(executor, "events", None)
        scope_for_schedule: Any = executor
        if callable(events_factory) and config.method in {"invoke", "stream"}:
            scope_for_schedule = events_factory(
                include=STUDIO_EVENT_CATEGORIES,
                auto_verbose=False,
            )
            logger.info(
                "Schedule for app %s: wrapped executor with events() (%s)",
                app_id,
                type(scope_for_schedule).__name__,
            )
        else:
            logger.warning(
                "Schedule for app %s: executor %s has no events() method; "
                "tool cards / assistant chunks will not stream to UI",
                app_id,
                type(executor).__name__,
            )

        builder = self._build_builder(executor, config)
        # Re-point the runner's scope at the events-wrapped invocable so the
        # runner's `getattr(scope, method)` resolves to EventInvocationBuilder.
        # invoke (which sets up the router reporter) instead of bare executor
        # .invoke. We still pass `executor` to _build_builder() so any APIs
        # that need the raw scope (jitter, retry) are unaffected.
        if scope_for_schedule is not executor:
            builder._scope = scope_for_schedule  # type: ignore[attr-defined]

        prompt_messages = self._resolve_prompt(app_id, config)
        job = self._invoke_builder(builder, config, prompt_messages)
        self._wire_fire_event_bridge(job, app_id, config, prompt_messages)

        with self._lock:
            self._jobs_by_app[app_id] = job
            self._configs_by_app[app_id] = config
        return self._summarize(app_id, job, config)

    def stop(self, app_id: str, *, drain: bool = True) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_app.get(app_id)
            cfg = self._configs_by_app.get(app_id)
        if job is None or cfg is None:
            return None
        job.stop(drain=drain, timeout=10)
        # Bridges stay around so the user can scroll back through completed
        # runs after stopping. They're cleaned up by remove().
        return self._summarize(app_id, job, cfg)

    def pause(self, app_id: str) -> ScheduleJobSummary | None:
        return self._mutate(app_id, lambda job: job.pause())

    def resume(self, app_id: str) -> ScheduleJobSummary | None:
        return self._mutate(app_id, lambda job: job.resume())

    def trigger_now(self, app_id: str) -> ScheduleJobSummary | None:
        # Log every manual trigger so a runaway client (key-repeat, SPA
        # double-submit, retry-on-error loop) is visible in the studio log.
        logger.info("Schedule for app %s: manual trigger_now requested", app_id)
        return self._mutate(app_id, lambda job: job.trigger_now())

    def remove(self, app_id: str) -> None:
        with self._lock:
            job = self._jobs_by_app.pop(app_id, None)
            self._configs_by_app.pop(app_id, None)
            self._app_locks.pop(app_id, None)
        if job is not None:
            job.stop(drain=False, timeout=5)
        self._drain_fire_bridges(app_id)
        # Drop the per-app push bridge too — a future schedule on the same
        # app creates a fresh one on first fire.
        remove_event_bridge(_app_event_bridge_id(app_id))

    def get_app_event_bridge(self, app_id: str) -> EventBridge:
        """Return the per-app schedule-activity push bridge, creating it on
        first call. Used by the SSE route — kept create-on-demand so the
        frontend can subscribe before any fire has happened.
        """
        bridge_id = _app_event_bridge_id(app_id)
        bridge = get_event_bridge(bridge_id)
        if bridge is None:
            bridge = create_event_bridge(bridge_id)
        elif bridge._closed:
            bridge.reopen()
        return bridge

    def _emit_app_event(
        self,
        app_id: str,
        event_name: str,
        data: dict[str, Any],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Push an event onto the per-app activity bridge.

        Called from on_fire / on_terminal / on_skip closures so the frontend
        sees fire transitions instantly, without waiting for the next
        ``GET /api/schedules`` poll to land.
        """
        bridge = self.get_app_event_bridge(app_id)
        asyncio.run_coroutine_threadsafe(bridge.emit(event_name, data), loop)

    # MARK: - Helpers

    def _mutate(self, app_id: str, action: Any) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_app.get(app_id)
            cfg = self._configs_by_app.get(app_id)
        if job is None or cfg is None:
            return None
        action(job)
        return self._summarize(app_id, job, cfg)

    def _resolve_executor(self, app_id: str) -> Any:
        registry = get_registry()
        app = registry.get(app_id)
        if app is None:
            raise ValueError(f"App not found: {app_id}")
        loaded = get_app_loader().load(app)
        executor = loaded.executor
        if executor is None:
            raise ValueError(f"App {app_id} has no agent or swarm executor")
        return executor

    def _resolve_prompt(self, app_id: str, config: ScheduleConfig) -> list[HumanMessage]:
        # Inline composer text wins over a saved-prompt reference so the user
        # can tweak the prompt without picking it from a dropdown.
        if config.prompt_text and config.prompt_text.strip():
            return [HumanMessage(content=config.prompt_text)]
        registry = get_registry()
        app = registry.get(app_id)
        if app is None:
            raise ValueError(f"App not found: {app_id}")
        loaded = get_app_loader().load(app)
        prompt = None
        if config.prompt_id:
            prompt = loaded.get_prompt(config.prompt_id)  # type: ignore[attr-defined]
        if prompt is None:
            prompt = loaded.get_default_prompt()
        if prompt is None:
            raise ValueError(f"App {app_id} has no prompts to schedule")
        return [HumanMessage(content=prompt.content)]

    def _build_builder(self, executor: Any, config: ScheduleConfig) -> Any:
        jitter = self._build_jitter(config)
        retry = self._build_retry(config)

        common_kwargs: dict[str, Any] = {
            "tz": config.tz,
            "jitter": jitter,
            "name": config.name,
            "max_runs": config.max_runs,
            "end_at": config.end_at,
            "retry": retry,
        }

        if config.schedule_type == "cron":
            if not config.cron_expression:
                raise ValueError("cron_expression is required for schedule_type='cron'")
            return executor.cron(
                config.cron_expression,
                misfire=config.misfire,
                max_overlap=config.max_overlap,
                overlap_policy=config.overlap_policy,
                **common_kwargs,
            )
        if config.schedule_type == "interval":
            if not config.interval_seconds:
                raise ValueError("interval_seconds is required for schedule_type='interval'")
            return executor.every(
                timedelta(seconds=config.interval_seconds),
                misfire=config.misfire,
                max_overlap=config.max_overlap,
                overlap_policy=config.overlap_policy,
                **common_kwargs,
            )
        if config.schedule_type == "at":
            if not config.fire_at:
                raise ValueError("fire_at is required for schedule_type='at'")
            return executor.at(
                config.fire_at,
                tz=config.tz,
                jitter=jitter,
                name=config.name,
                retry=retry,
            )
        raise ValueError(f"Unknown schedule type: {config.schedule_type}")

    def _build_jitter(self, config: ScheduleConfig) -> JitterSpec | None:
        if config.jitter_min_seconds == 0 and config.jitter_max_seconds == 0:
            return None
        align = (
            timedelta(seconds=config.jitter_align_seconds)
            if config.jitter_align_seconds is not None
            else None
        )
        return JitterSpec(
            min=timedelta(seconds=config.jitter_min_seconds),
            max=timedelta(seconds=config.jitter_max_seconds),
            distribution=config.jitter_distribution,
            align_to=align,
            skip_if_overruns_next=config.jitter_skip_if_overruns_next,
            seed=config.jitter_seed,
        )

    def _build_retry(self, config: ScheduleConfig) -> Retry:
        max_delay = (
            timedelta(seconds=config.retry_max_delay_seconds)
            if config.retry_max_delay_seconds is not None
            else None
        )
        return Retry(
            max_attempts=config.retry_max_attempts,
            backoff=config.retry_backoff,
            base=timedelta(seconds=config.retry_base_seconds),
            factor=config.retry_factor,
            max_delay=max_delay,
        )

    def _invoke_builder(
        self,
        builder: Any,
        config: ScheduleConfig,
        messages: list[HumanMessage],
    ) -> ScheduledJob:
        method = config.method
        if method == "invoke":
            return builder.invoke(messages)
        if method == "ainvoke":
            return builder.ainvoke(messages)
        if method == "stream":
            return builder.stream(messages)
        if method == "astream":
            return builder.astream(messages)
        if method == "batch":
            return builder.batch([messages])
        if method == "abatch":
            return builder.abatch([messages])
        raise ValueError(f"Unsupported method: {method}")

    def _summarize(
        self,
        app_id: str,
        job: ScheduledJob,
        config: ScheduleConfig,
    ) -> ScheduleJobSummary:
        completed = job.history(limit=20)
        completed_ids = {record.fire_id for record in completed}
        # Filter active runs to this job — a previous job's slow fire can land
        # in active_runs after start() drained the map (its on_fire closure
        # writes by app_id, not job_id). Without this filter the new job's
        # summary surfaces stale runs the user can't subscribe to and can't
        # explain.
        active = [
            r
            for r in self._active_runs_by_app.get(app_id, {}).values()
            if r.metadata.get("job_id") == job.id
        ]
        # An in-flight record may briefly exist in both maps if a callback
        # races the dispatch loop; trust history's copy so we don't render a
        # stale "running" pill for a fire that just finished.
        merged: list[RunRecord] = [r for r in active if r.fire_id not in completed_ids]
        merged.extend(completed)
        merged.sort(key=lambda record: record.scheduled_at)
        history = [self._summarize_run(record) for record in merged[-20:]]
        # Fall back to the schedule's first upcoming fire when the SDK's
        # run loop hasn't iterated yet (which is the case immediately after
        # start — _next_run_at is set inside the loop). Without this the
        # initial PUT response carries next_run_at=None and the upcoming
        # card sits as "waiting for first run" until the first fire lands.
        upcoming = job.next_runs(5)
        next_run_at = job.next_run_at or (upcoming[0] if upcoming else None)
        return ScheduleJobSummary(
            job_id=job.id,
            app_id=app_id,
            name=job.name,
            config=config,
            is_running=job.is_running,
            is_paused=job.is_paused,
            is_done=job.is_done,
            fire_count=job.fire_count,
            success_count=job.success_count,
            failure_count=job.failure_count,
            skip_count=job.skip_count,
            next_run_at=next_run_at,
            upcoming=upcoming,
            history=history,
        )

    def _summarize_run(self, record: RunRecord) -> ScheduleRunSummary:
        event_session_id = record.metadata.get("event_session_id") if record.metadata else None
        return ScheduleRunSummary(
            fire_id=record.fire_id,
            scheduled_at=record.scheduled_at,
            fired_at=record.fired_at,
            finished_at=record.finished_at,
            status=record.status,
            attempt=record.attempt,
            jitter_offset_seconds=record.jitter_offset.total_seconds(),
            error=str(record.error) if record.error is not None else None,
            event_session_id=event_session_id if isinstance(event_session_id, str) else None,
        )

    # MARK: - Per-fire event bridge

    def _wire_fire_event_bridge(
        self,
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

        prompt_text = prompt_messages[0].content if prompt_messages else ""

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

            event_session_id = _fire_event_session_id(job.id, record.fire_id)
            record.metadata["event_session_id"] = event_session_id
            # Tag with job_id so _summarize can drop active runs that belong
            # to a previous job (its on_fire still mutates this shared map).
            record.metadata["job_id"] = job.id

            with self._lock:
                self._active_runs_by_app.setdefault(app_id, {})[record.fire_id] = record
                session_ids = self._fire_session_ids_by_app.setdefault(app_id, [])
                if event_session_id not in session_ids:
                    session_ids.append(event_session_id)

            bridge = get_event_bridge(event_session_id)
            if bridge is None:
                bridge = create_event_bridge(event_session_id)
            elif bridge._closed:
                bridge.reopen()

            reporter = StudioReporter(bridge, loop)

            # ContextVars set in this callback persist for the rest of the
            # runner Task, so the upcoming executor invoke picks up the
            # reporter and delivery mode.
            current_reporter.set(reporter)
            current_sdk_delivery_mode.set(delivery_mode)
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
            asyncio.run_coroutine_threadsafe(
                bridge.emit(
                    "session_start",
                    {
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
                    },
                ),
                loop,
            )

            # Push to the per-app activity bridge so the frontend renders
            # the run card the instant the fire starts. The event carries
            # event_session_id so the chat-style stream at
            # /fires/{fire_id}/events can be opened immediately, and
            # next_run_at so the upcoming-card countdown rolls over to the
            # next tick without waiting for a poll.
            self._emit_app_event(
                app_id,
                "schedule_fire_started",
                {
                    "app_id": app_id,
                    "fire_id": record.fire_id,
                    "event_session_id": event_session_id,
                    "scheduled_at": record.scheduled_at.isoformat(),
                    "fired_at": record.fired_at.isoformat() if record.fired_at else None,
                    "attempt": record.attempt,
                    "next_run_at": _predict_next_run_iso(job, record.scheduled_at),
                },
                loop,
            )

        def _on_terminal(record: RunRecord, *, terminal: str) -> None:
            with self._lock:
                self._active_runs_by_app.get(app_id, {}).pop(record.fire_id, None)

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

            asyncio.run_coroutine_threadsafe(
                bridge.emit(
                    "turn_complete" if terminal == "success" else "error",
                    _build_terminal_event_data(
                        session_id=event_session_id,
                        schedule_fire_id=record.fire_id,
                        status=record.status,
                        duration_ms=_duration_ms(record),
                        error=str(record.error) if record.error else None,
                        result=record.result,
                    ),
                ),
                loop,
            )

            # Push to the per-app bridge so the frontend flips the card's
            # status pill from running -> succeeded/failed without waiting
            # for the next reconciliation poll.
            self._emit_app_event(
                app_id,
                "schedule_fire_completed",
                {
                    "app_id": app_id,
                    "fire_id": record.fire_id,
                    "status": record.status,
                    "finished_at": (record.finished_at.isoformat() if record.finished_at else None),
                    "error": str(record.error) if record.error else None,
                    "duration_ms": _duration_ms(record),
                    # Computed from now (not the fire's scheduled time) so a
                    # long-running fire that overran one or more cron ticks
                    # reports the actual next future tick, not one already
                    # in the past.
                    "next_run_at": _predict_next_run_iso(
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
            with self._lock:
                self._active_runs_by_app.get(app_id, {}).pop(record.fire_id, None)
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            self._emit_app_event(
                app_id,
                "schedule_fire_skipped",
                {
                    "app_id": app_id,
                    "fire_id": record.fire_id,
                    "status": record.status,
                    "scheduled_at": record.scheduled_at.isoformat(),
                    "next_run_at": _predict_next_run_iso(job, record.scheduled_at),
                },
                loop,
            )

        job.on_fire(_on_fire)
        job.on_success(lambda record: _on_terminal(record, terminal="success"))
        job.on_error(lambda record: _on_terminal(record, terminal="error"))
        job.on_skip(_on_skip)

    def _drain_fire_bridges(self, app_id: str) -> None:
        with self._lock:
            session_ids = self._fire_session_ids_by_app.pop(app_id, [])
            self._active_runs_by_app.pop(app_id, None)
        for session_id in session_ids:
            remove_event_bridge(session_id)


def _duration_ms(record: RunRecord) -> int | None:
    if record.fired_at is None or record.finished_at is None:
        return None
    return int((record.finished_at - record.fired_at).total_seconds() * 1000)


def _serialize_structured_result(result: Any) -> Any:
    if result is None:
        return None
    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


def _serialize_token_usage(token_usage: Any) -> dict[str, int] | None:
    if token_usage is None:
        return None
    return {
        "total_tokens": getattr(token_usage, "total_tokens", 0),
        "input_tokens": getattr(token_usage, "input_tokens", 0),
        "output_tokens": getattr(token_usage, "output_tokens", 0),
        "cache_read_tokens": getattr(token_usage, "cache_read_tokens", 0),
        "cache_creation_tokens": getattr(token_usage, "cache_creation_tokens", 0),
        "reasoning_tokens": getattr(token_usage, "reasoning_tokens", 0),
    }


def _coerce_stream_result(result: Any) -> Any:
    """Convert a stream method's list-of-events result into a SessionResponse.

    ``stream`` / ``astream`` runners return ``list(events)``; the last
    contract event carries the same final payload an ``invoke`` would have
    returned. Clients reconnecting after a fire completes need that payload
    in ``turn_complete`` so the UI can render the response without replaying
    every chunk.
    """
    if not isinstance(result, list):
        return result
    from maivn_shared import FINAL_EVENT_NAME
    from maivn_shared import SessionResponse as SDKSessionResponse

    final_payload: dict[str, Any] | None = None
    for event in result:
        payload = getattr(event, "payload", None)
        if not isinstance(payload, dict):
            continue
        if getattr(event, "name", "") == FINAL_EVENT_NAME or payload.get("event_name") == "final":
            final_payload = payload
    if final_payload is None:
        return result
    try:
        return SDKSessionResponse.model_validate(final_payload)
    except Exception:  # noqa: BLE001 - falling back is harmless; chunks have already streamed
        return result


def _extract_result_payload(result: Any) -> dict[str, Any]:
    result = _coerce_stream_result(result)
    responses = getattr(result, "responses", None)
    response_text = latest_response_text(responses)
    if response_text is None:
        raw_response = getattr(result, "response", None)
        response_text = raw_response if isinstance(raw_response, str) else ""

    result_payload = _serialize_structured_result(getattr(result, "result", None))
    token_usage = _serialize_token_usage(getattr(result, "token_usage", None))

    payload: dict[str, Any] = {
        "responses": responses if isinstance(responses, list) else [],
        "response": response_text,
        "result": result_payload,
        "token_usage": token_usage,
    }
    return {key: value for key, value in payload.items() if value is not None}


def _build_terminal_event_data(**base: Any) -> dict[str, Any]:
    result = base.pop("result", None)
    result_payload = _extract_result_payload(result)
    output = {
        "response": result_payload.get("response"),
        "result": result_payload.get("result"),
        "token_usage": result_payload.get("token_usage"),
    }
    return {
        **base,
        **result_payload,
        "output": {key: value for key, value in output.items() if value is not None},
    }


_manager: ScheduleManager | None = None
_manager_lock = threading.Lock()


def get_schedule_manager() -> ScheduleManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScheduleManager()
        return _manager


__all__ = ["ScheduleManager", "get_schedule_manager"]
