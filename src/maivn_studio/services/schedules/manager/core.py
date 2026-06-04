"""Live :class:`ScheduleManager` — owns the per-app schedule registry."""

# pyright: strict

from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable

from maivn import RunRecord, ScheduledJob
from maivn.messages import HumanMessage

from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.app_loader.loader import get_app_loader
from maivn_studio.services.event_bridge import (
    EventBridge,
    create_event_bridge,
    get_event_bridge,
    remove_event_bridge,
)
from maivn_studio.services.session_manager.models import STUDIO_EVENT_CATEGORIES

from ..models import ScheduleConfig, ScheduleJobSummary, ScheduleRunSummary
from .builders import Executor, build_builder, invoke_builder
from .fire_bridge import wire_fire_event_bridge
from .ids import app_event_bridge_id

logger = logging.getLogger(__name__)


# MARK: ScheduleManager


class ScheduleManager:
    """Owns the set of Studio-driven scheduled jobs, indexed by app."""

    def __init__(self) -> None:
        self.lock: threading.Lock = threading.Lock()
        self._jobs_by_app: dict[str, ScheduledJob] = {}
        self._configs_by_app: dict[str, ScheduleConfig] = {}
        # Track in-flight fires so the UI can render a card before the run
        # completes (history is only populated after _execute_run's finally
        # block). Keyed by app_id → {fire_id: RunRecord}.
        self.active_runs_by_app: dict[str, dict[str, RunRecord]] = {}
        # Track all event-session ids we've created per app so removing a
        # schedule cleans up bridges instead of leaking them.
        self.fire_session_ids_by_app: dict[str, list[str]] = {}
        # Per-app locks serialize start() calls — without this, two concurrent
        # PUT /schedules/{app} requests can both pass the existence check and
        # create separate ScheduledJob instances. Both jobs then fire on every
        # cron tick, which is what manifested as the wave of skipped_overlap
        # records when the slow first job blocked the second one's slot.
        self._app_locks: dict[str, threading.Lock] = {}

    # MARK: - Public API

    def list_jobs(self) -> list[ScheduleJobSummary]:
        with self.lock:
            return [
                self._summarize(app_id, job, self._configs_by_app[app_id])
                for app_id, job in self._jobs_by_app.items()
            ]

    def get(self, app_id: str) -> ScheduleJobSummary | None:
        with self.lock:
            job = self._jobs_by_app.get(app_id)
            cfg = self._configs_by_app.get(app_id)
        if job is None or cfg is None:
            return None
        return self._summarize(app_id, job, cfg)

    def start(self, app_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
        # Per-app serialization: two concurrent PUT /schedules/{app} requests
        # would otherwise both pass the existence check, both call
        # invoke_builder (which immediately starts the job inside the SDK's
        # _build_job), and both write a different ScheduledJob into the
        # registry. Whichever store-call lands second wins the dict slot, but
        # the loser's _bootstrap task keeps running and firing — that's what
        # produced the dozens of skipped_overlap records the user reported.
        with self.lock:
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
        scope_for_schedule: object = executor
        if config.method in {"invoke", "stream"}:
            scope_for_schedule = executor.events(
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
                (
                    "Schedule for app %s: method %s does not stream through events(); "
                    + "tool cards / assistant chunks will not stream to UI"
                ),
                app_id,
                config.method,
            )

        builder = build_builder(executor, config)
        # Re-point the runner's scope at the events-wrapped invocable so the
        # runner's `getattr(scope, method)` resolves to EventInvocationBuilder.
        # invoke (which sets up the router reporter) instead of bare executor
        # .invoke. We still pass `executor` to build_builder() so any APIs
        # that need the raw scope (jitter, retry) are unaffected.
        if scope_for_schedule is not executor:
            _ = builder.with_scope(scope_for_schedule)

        prompt_messages = self._resolve_prompt(app_id, config)
        job = invoke_builder(builder, config, prompt_messages)
        wire_fire_event_bridge(self, job, app_id, config, prompt_messages)

        with self.lock:
            self._jobs_by_app[app_id] = job
            self._configs_by_app[app_id] = config
        return self._summarize(app_id, job, config)

    def stop(self, app_id: str, *, drain: bool = True) -> ScheduleJobSummary | None:
        with self.lock:
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
        with self.lock:
            job = self._jobs_by_app.pop(app_id, None)
            _ = self._configs_by_app.pop(app_id, None)
            _ = self._app_locks.pop(app_id, None)
        if job is not None:
            job.stop(drain=False, timeout=5)
        self._drain_fire_bridges(app_id)
        # Drop the per-app push bridge too — a future schedule on the same
        # app creates a fresh one on first fire.
        remove_event_bridge(app_event_bridge_id(app_id))

    def get_app_event_bridge(self, app_id: str) -> EventBridge:
        """Return the per-app schedule-activity push bridge, creating it on
        first call. Used by the SSE route — kept create-on-demand so the
        frontend can subscribe before any fire has happened.
        """
        bridge_id = app_event_bridge_id(app_id)
        bridge = get_event_bridge(bridge_id)
        if bridge is None:
            bridge = create_event_bridge(bridge_id)
        elif bridge.stream_is_closed:
            bridge.reopen()
        return bridge

    def emit_app_event(
        self,
        app_id: str,
        event_name: str,
        data: dict[str, object],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        """Push an event onto the per-app activity bridge.

        Called from on_fire / on_terminal / on_skip closures so the frontend
        sees fire transitions instantly, without waiting for the next
        ``GET /api/schedules`` poll to land.
        """
        bridge = self.get_app_event_bridge(app_id)
        _ = asyncio.run_coroutine_threadsafe(bridge.emit(event_name, data), loop)

    # MARK: - Helpers

    def _mutate(
        self,
        app_id: str,
        action: Callable[[ScheduledJob], object],
    ) -> ScheduleJobSummary | None:
        with self.lock:
            job = self._jobs_by_app.get(app_id)
            cfg = self._configs_by_app.get(app_id)
        if job is None or cfg is None:
            return None
        _ = action(job)
        return self._summarize(app_id, job, cfg)

    def _resolve_executor(self, app_id: str) -> Executor:
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
            prompt = loaded.get_prompt(config.prompt_id)
        if prompt is None:
            prompt = loaded.get_default_prompt()
        if prompt is None:
            raise ValueError(f"App {app_id} has no prompts to schedule")
        return [HumanMessage(content=prompt.content)]

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
            for r in self.active_runs_by_app.get(app_id, {}).values()
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

    def _drain_fire_bridges(self, app_id: str) -> None:
        with self.lock:
            session_ids = self.fire_session_ids_by_app.pop(app_id, [])
            _ = self.active_runs_by_app.pop(app_id, None)
        for session_id in session_ids:
            remove_event_bridge(session_id)


# MARK: Singleton


_manager: ScheduleManager | None = None
_manager_lock = threading.Lock()


def get_schedule_manager() -> ScheduleManager:
    """Return the process-wide :class:`ScheduleManager` singleton."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScheduleManager()
        return _manager


__all__ = ["ScheduleManager", "get_schedule_manager"]
