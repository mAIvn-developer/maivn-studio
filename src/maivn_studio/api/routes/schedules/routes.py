"""API route handlers for app cron-job scheduling."""

# pyright: strict

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from maivn_studio.services.event_bridge import create_event_bridge, get_event_bridge
from maivn_studio.services.schedules import (
    ScheduleConfig,
    ScheduleJobSummary,
    get_schedule_manager,
)

router = APIRouter(prefix="/api/schedules", tags=["schedules"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[ScheduleJobSummary])
async def list_jobs() -> list[ScheduleJobSummary]:
    """List all currently registered schedule jobs."""
    return get_schedule_manager().list_jobs()


@router.get("/{app_id}", response_model=ScheduleJobSummary)
async def get_job(app_id: str) -> ScheduleJobSummary:
    """Return the schedule summary for ``app_id`` or 404 if none is registered."""
    summary = get_schedule_manager().get(app_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")
    return summary


@router.put("/{app_id}", response_model=ScheduleJobSummary)
async def upsert_job(app_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
    """Create or replace the schedule for ``app_id``."""
    try:
        return get_schedule_manager().start(app_id, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{app_id}/stop", response_model=ScheduleJobSummary)
async def stop_job(app_id: str, drain: bool = True) -> ScheduleJobSummary:
    """Stop the schedule for ``app_id``, optionally draining in-flight fires."""
    summary = get_schedule_manager().stop(app_id, drain=drain)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")
    return summary


@router.post("/{app_id}/pause", response_model=ScheduleJobSummary)
async def pause_job(app_id: str) -> ScheduleJobSummary:
    """Pause future fires for ``app_id`` without losing its configuration."""
    summary = get_schedule_manager().pause(app_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")
    return summary


@router.post("/{app_id}/resume", response_model=ScheduleJobSummary)
async def resume_job(app_id: str) -> ScheduleJobSummary:
    """Resume a previously paused schedule for ``app_id``."""
    summary = get_schedule_manager().resume(app_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")
    return summary


@router.post("/{app_id}/trigger", response_model=ScheduleJobSummary)
async def trigger_now(app_id: str) -> ScheduleJobSummary:
    """Fire the scheduled app immediately, outside its cron cadence."""
    summary = get_schedule_manager().trigger_now(app_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")
    return summary


@router.delete("/{app_id}", status_code=204)
async def remove_job(app_id: str) -> None:
    """Delete the schedule and its history for ``app_id``."""
    get_schedule_manager().remove(app_id)


@router.get("/{app_id}/events")
async def get_app_schedule_events(
    app_id: str,
    last_event_id: str | None = None,
) -> EventSourceResponse:
    """Stream per-app schedule activity push notifications.

    Frontend subscribes once per app and learns about new fires the instant
    the SDK's on_fire callback runs (no polling needed for the
    countdown -> running transition). Each ``schedule_fire_started`` event
    carries the new fire's ``event_session_id`` so the chat-style per-fire
    stream at ``/fires/{fire_id}/events`` can be opened immediately.
    """
    bridge = get_schedule_manager().get_app_event_bridge(app_id)
    return EventSourceResponse(bridge.generate_sse(last_event_id=last_event_id))


@router.get("/{app_id}/fires/{fire_id}/events")
async def get_fire_events(
    app_id: str,
    fire_id: str,
    last_event_id: str | None = None,
) -> EventSourceResponse:
    """Stream the same SSE events a chat session emits, but for a single
    scheduled fire. The event bridge is created lazily by the schedule
    manager's on_fire callback; if a frontend connects before that callback
    runs we still create an empty bridge so reconnects (with last_event_id)
    can resume cleanly once events start landing.
    """
    summary = get_schedule_manager().get(app_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for app {app_id}")

    record = next((r for r in summary.history if r.fire_id == fire_id), None)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fire {fire_id} not found for app {app_id}",
        )

    if not record.event_session_id:
        raise HTTPException(
            status_code=409,
            detail="Fire has not started executing yet — no event stream available",
        )

    bridge = get_event_bridge(record.event_session_id)
    if bridge is None:
        bridge = create_event_bridge(record.event_session_id)

    return EventSourceResponse(bridge.generate_sse(last_event_id=last_event_id))
