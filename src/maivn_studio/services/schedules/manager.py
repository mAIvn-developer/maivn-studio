"""Manages live ScheduledJob instances configured through Studio."""

from __future__ import annotations

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
from maivn.messages import HumanMessage

from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.demo_loader.loader import get_demo_loader

from .models import ScheduleConfig, ScheduleJobSummary, ScheduleRunSummary

logger = logging.getLogger(__name__)


class ScheduleManager:
    """Owns the set of Studio-driven scheduled jobs, indexed by demo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._jobs_by_demo: dict[str, ScheduledJob] = {}
        self._configs_by_demo: dict[str, ScheduleConfig] = {}

    # MARK: - Public API

    def list_jobs(self) -> list[ScheduleJobSummary]:
        with self._lock:
            return [
                self._summarize(demo_id, job, self._configs_by_demo[demo_id])
                for demo_id, job in self._jobs_by_demo.items()
            ]

    def get(self, demo_id: str) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_demo.get(demo_id)
            cfg = self._configs_by_demo.get(demo_id)
        if job is None or cfg is None:
            return None
        return self._summarize(demo_id, job, cfg)

    def start(self, demo_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
        existing = self._jobs_by_demo.get(demo_id)
        if existing is not None and not existing.is_done:
            existing.stop(drain=False, timeout=5)

        executor = self._resolve_executor(demo_id)
        builder = self._build_builder(executor, config)
        prompt_messages = self._resolve_prompt(demo_id, config)

        job = self._invoke_builder(builder, config, prompt_messages)

        with self._lock:
            self._jobs_by_demo[demo_id] = job
            self._configs_by_demo[demo_id] = config
        return self._summarize(demo_id, job, config)

    def stop(self, demo_id: str, *, drain: bool = True) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_demo.get(demo_id)
            cfg = self._configs_by_demo.get(demo_id)
        if job is None or cfg is None:
            return None
        job.stop(drain=drain, timeout=10)
        return self._summarize(demo_id, job, cfg)

    def pause(self, demo_id: str) -> ScheduleJobSummary | None:
        return self._mutate(demo_id, lambda job: job.pause())

    def resume(self, demo_id: str) -> ScheduleJobSummary | None:
        return self._mutate(demo_id, lambda job: job.resume())

    def trigger_now(self, demo_id: str) -> ScheduleJobSummary | None:
        return self._mutate(demo_id, lambda job: job.trigger_now())

    def remove(self, demo_id: str) -> None:
        with self._lock:
            job = self._jobs_by_demo.pop(demo_id, None)
            self._configs_by_demo.pop(demo_id, None)
        if job is not None:
            job.stop(drain=False, timeout=5)

    # MARK: - Helpers

    def _mutate(self, demo_id: str, action: Any) -> ScheduleJobSummary | None:
        with self._lock:
            job = self._jobs_by_demo.get(demo_id)
            cfg = self._configs_by_demo.get(demo_id)
        if job is None or cfg is None:
            return None
        action(job)
        return self._summarize(demo_id, job, cfg)

    def _resolve_executor(self, demo_id: str) -> Any:
        registry = get_registry()
        demo = registry.get(demo_id)
        if demo is None:
            raise ValueError(f"Demo not found: {demo_id}")
        loaded = get_demo_loader().load(demo)
        executor = loaded.executor
        if executor is None:
            raise ValueError(f"Demo {demo_id} has no agent or swarm executor")
        return executor

    def _resolve_prompt(self, demo_id: str, config: ScheduleConfig) -> list[HumanMessage]:
        registry = get_registry()
        demo = registry.get(demo_id)
        if demo is None:
            raise ValueError(f"Demo not found: {demo_id}")
        loaded = get_demo_loader().load(demo)
        prompt = None
        if config.prompt_id:
            prompt = loaded.get_prompt(config.prompt_id)  # type: ignore[attr-defined]
        if prompt is None:
            prompt = loaded.get_default_prompt()
        if prompt is None:
            raise ValueError(f"Demo {demo_id} has no prompts to schedule")
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
        demo_id: str,
        job: ScheduledJob,
        config: ScheduleConfig,
    ) -> ScheduleJobSummary:
        history = [self._summarize_run(record) for record in job.history(limit=20)]
        return ScheduleJobSummary(
            job_id=job.id,
            demo_id=demo_id,
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
        return ScheduleRunSummary(
            fire_id=record.fire_id,
            scheduled_at=record.scheduled_at,
            fired_at=record.fired_at,
            finished_at=record.finished_at,
            status=record.status,
            attempt=record.attempt,
            jitter_offset_seconds=record.jitter_offset.total_seconds(),
            error=str(record.error) if record.error is not None else None,
        )


_manager: ScheduleManager | None = None
_manager_lock = threading.Lock()


def get_schedule_manager() -> ScheduleManager:
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = ScheduleManager()
        return _manager


__all__ = ["ScheduleManager", "get_schedule_manager"]
