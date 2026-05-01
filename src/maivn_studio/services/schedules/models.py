"""Pydantic models for Studio schedule configuration and reporting."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ScheduleConfig(BaseModel):
    """User-supplied schedule configuration for an app."""

    schedule_type: Literal["cron", "interval", "at"] = "cron"
    cron_expression: str | None = None
    interval_seconds: float | None = None
    fire_at: datetime | None = None

    tz: str = "UTC"

    jitter_min_seconds: float = 0.0
    jitter_max_seconds: float = 0.0
    jitter_distribution: Literal["uniform", "normal", "triangular"] = "uniform"
    jitter_align_seconds: float | None = None
    jitter_seed: int | None = None
    jitter_skip_if_overruns_next: bool = True

    method: Literal["invoke", "stream", "batch", "abatch", "ainvoke", "astream"] = "stream"
    # Inline prompt text. When set, this is the prompt every fire sends —
    # mirrors what the user typed into the composer when they switched the
    # composer to "Schedule" mode. Takes precedence over prompt_id so users
    # can edit the prompt mid-run via "Update schedule".
    prompt_text: str | None = None
    prompt_id: str | None = None

    misfire: Literal["skip", "fire_now", "coalesce"] = "coalesce"
    overlap_policy: Literal["skip", "queue", "replace"] = "skip"
    max_overlap: int = 1
    max_runs: int | None = None
    end_at: datetime | None = None

    retry_max_attempts: int = 1
    retry_backoff: Literal["constant", "linear", "exponential"] = "constant"
    retry_base_seconds: float = 5.0
    retry_factor: float = 2.0
    retry_max_delay_seconds: float | None = 600.0

    name: str | None = None


class ScheduleRunSummary(BaseModel):
    fire_id: str
    scheduled_at: datetime
    fired_at: datetime | None = None
    finished_at: datetime | None = None
    status: str
    attempt: int
    jitter_offset_seconds: float
    error: str | None = None
    # Synthetic session id used to subscribe to this fire's event stream.
    # Set when the fire actually runs (i.e., once an EventBridge has been
    # registered for it). The frontend hits /api/schedules/{app}/fires/
    # {fire_id}/events to stream the same events a chat session emits.
    event_session_id: str | None = None


class ScheduleJobSummary(BaseModel):
    job_id: str
    app_id: str
    name: str
    config: ScheduleConfig
    is_running: bool
    is_paused: bool
    is_done: bool
    fire_count: int
    success_count: int
    failure_count: int
    skip_count: int
    next_run_at: datetime | None = None
    upcoming: list[datetime] = Field(default_factory=list)
    history: list[ScheduleRunSummary] = Field(default_factory=list)
