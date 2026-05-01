"""API route handlers for demo cron-job scheduling."""

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
    return get_schedule_manager().list_jobs()


@router.get("/{demo_id}", response_model=ScheduleJobSummary)
async def get_job(demo_id: str) -> ScheduleJobSummary:
    summary = get_schedule_manager().get(demo_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")
    return summary


@router.put("/{demo_id}", response_model=ScheduleJobSummary)
async def upsert_job(demo_id: str, config: ScheduleConfig) -> ScheduleJobSummary:
    try:
        return get_schedule_manager().start(demo_id, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{demo_id}/stop", response_model=ScheduleJobSummary)
async def stop_job(demo_id: str, drain: bool = True) -> ScheduleJobSummary:
    summary = get_schedule_manager().stop(demo_id, drain=drain)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")
    return summary


@router.post("/{demo_id}/pause", response_model=ScheduleJobSummary)
async def pause_job(demo_id: str) -> ScheduleJobSummary:
    summary = get_schedule_manager().pause(demo_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")
    return summary


@router.post("/{demo_id}/resume", response_model=ScheduleJobSummary)
async def resume_job(demo_id: str) -> ScheduleJobSummary:
    summary = get_schedule_manager().resume(demo_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")
    return summary


@router.post("/{demo_id}/trigger", response_model=ScheduleJobSummary)
async def trigger_now(demo_id: str) -> ScheduleJobSummary:
    summary = get_schedule_manager().trigger_now(demo_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")
    return summary


@router.delete("/{demo_id}", status_code=204)
async def remove_job(demo_id: str) -> None:
    get_schedule_manager().remove(demo_id)


@router.get("/{demo_id}/fires/{fire_id}/events")
async def get_fire_events(
    demo_id: str,
    fire_id: str,
    last_event_id: str | None = None,
) -> EventSourceResponse:
    """Stream the same SSE events a chat session emits, but for a single
    scheduled fire. The event bridge is created lazily by the schedule
    manager's on_fire callback; if a frontend connects before that callback
    runs we still create an empty bridge so reconnects (with last_event_id)
    can resume cleanly once events start landing.
    """
    summary = get_schedule_manager().get(demo_id)
    if summary is None:
        raise HTTPException(status_code=404, detail=f"No schedule for demo {demo_id}")

    record = next((r for r in summary.history if r.fire_id == fire_id), None)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail=f"Fire {fire_id} not found for demo {demo_id}",
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
