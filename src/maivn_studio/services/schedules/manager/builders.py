"""ScheduledJob builder helpers — jitter / retry specs and the per-method dispatch.

Pulled out of :class:`ScheduleManager` so the class stays focused on lifecycle
state. These are free functions because they don't read any manager state.
"""

# pyright: strict

from __future__ import annotations

from datetime import timedelta

from maivn import (
    Agent,
    CronInvocationBuilder,
    JitterSpec,
    Retry,
    ScheduledJob,
    Swarm,
)
from maivn.messages import HumanMessage

from ..models import ScheduleConfig

# An executor is either a single agent or a swarm — both expose the SDK
# scheduling entry points (`cron` / `every` / `at`).
Executor = Agent | Swarm


# MARK: Spec builders


def build_jitter(config: ScheduleConfig) -> JitterSpec | None:
    """Translate the user's jitter config into a SDK ``JitterSpec``, or ``None``."""
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


def build_retry(config: ScheduleConfig) -> Retry:
    """Translate the user's retry config into a SDK ``Retry`` spec."""
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


# MARK: Builder construction / dispatch


def build_builder(executor: Executor, config: ScheduleConfig) -> CronInvocationBuilder:
    """Construct the SDK schedule builder (cron / interval / at) for the executor."""
    jitter = build_jitter(config)
    retry = build_retry(config)

    if config.schedule_type == "cron":
        if not config.cron_expression:
            raise ValueError("cron_expression is required for schedule_type='cron'")
        return executor.cron(
            config.cron_expression,
            tz=config.tz,
            jitter=jitter,
            name=config.name,
            misfire=config.misfire,
            max_overlap=config.max_overlap,
            overlap_policy=config.overlap_policy,
            end_at=config.end_at,
            max_runs=config.max_runs,
            retry=retry,
        )
    if config.schedule_type == "interval":
        if not config.interval_seconds:
            raise ValueError("interval_seconds is required for schedule_type='interval'")
        return executor.every(
            timedelta(seconds=config.interval_seconds),
            tz=config.tz,
            jitter=jitter,
            name=config.name,
            misfire=config.misfire,
            max_overlap=config.max_overlap,
            overlap_policy=config.overlap_policy,
            end_at=config.end_at,
            max_runs=config.max_runs,
            retry=retry,
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


def invoke_builder(
    builder: CronInvocationBuilder,
    config: ScheduleConfig,
    messages: list[HumanMessage],
) -> ScheduledJob:
    """Dispatch the appropriate ``builder.<method>`` call for ``config.method``."""
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


__all__ = [
    "Executor",
    "build_builder",
    "build_jitter",
    "build_retry",
    "invoke_builder",
]
