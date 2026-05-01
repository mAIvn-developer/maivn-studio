"""Manages live ScheduledJob instances configured through Studio."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import timedelta
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
    create_event_bridge,
    get_event_bridge,
    remove_event_bridge,
)
from maivn_studio.services.session_manager.models import (
    _STUDIO_EVENT_CATEGORIES,
    _latest_response_text,
)
from maivn_studio.services.studio_reporter.reporter import StudioReporter

from .models import ScheduleConfig, ScheduleJobSummary, ScheduleRunSummary

logger = logging.getLogger(__name__)


def _fire_event_session_id(job_id: str, fire_id: str) -> str:
    """Synthetic session id for a single scheduled fire's event bridge.

    Format is intentionally distinct from real session ids so a stray lookup
    can be diagnosed in logs.
    """
    return f"schedule:{job_id}:{fire_id}"


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
        existing = self._jobs_by_app.get(app_id)
        if existing is not None and not existing.is_done:
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
                include=_STUDIO_EVENT_CATEGORIES,
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
        return self._mutate(app_id, lambda job: job.trigger_now())

    def remove(self, app_id: str) -> None:
        with self._lock:
            job = self._jobs_by_app.pop(app_id, None)
            self._configs_by_app.pop(app_id, None)
        if job is not None:
            job.stop(drain=False, timeout=5)
        self._drain_fire_bridges(app_id)

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
        active = list(self._active_runs_by_app.get(app_id, {}).values())
        # An in-flight record may briefly exist in both maps if a callback
        # races the dispatch loop; trust history's copy so we don't render a
        # stale "running" pill for a fire that just finished.
        merged: list[RunRecord] = [r for r in active if r.fire_id not in completed_ids]
        merged.extend(completed)
        merged.sort(key=lambda record: record.scheduled_at)
        history = [self._summarize_run(record) for record in merged[-20:]]
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
            next_run_at=job.next_run_at,
            upcoming=job.next_runs(5),
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

            event_session_id = _fire_event_session_id(job.id, record.fire_id)
            record.metadata["event_session_id"] = event_session_id

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

            # Bridge stays in the registry so a card that subscribes after
            # the fire completes still gets to replay history. Cleanup
            # happens when the schedule itself is stopped or removed.

        # Skipped fires (overlap / jitter / misfire) never trigger on_fire,
        # so on_skip just removes any stale active record for parity.
        def _on_skip(record: RunRecord) -> None:
            with self._lock:
                self._active_runs_by_app.get(app_id, {}).pop(record.fire_id, None)

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


def _extract_result_payload(result: Any) -> dict[str, Any]:
    responses = getattr(result, "responses", None)
    response_text = _latest_response_text(responses)
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
