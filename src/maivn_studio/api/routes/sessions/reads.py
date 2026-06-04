# pyright: strict

from __future__ import annotations

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from maivn_studio.services.event_bridge import create_event_bridge, get_event_bridge
from maivn_studio.services.session_manager.manager import get_session_manager
from maivn_studio.services.session_manager.models import SessionStatus

from .helpers import get_session_or_404, session_response
from .models import SessionListResponse, SessionResponse

router = APIRouter()


async def list_sessions(
    status: str | None = None,
    thread_id: str | None = None,
) -> SessionListResponse:
    """List sessions, optionally filtered by status and/or thread id."""
    manager = get_session_manager()

    if thread_id:
        sessions = manager.get_by_thread(thread_id)
    else:
        sessions = manager.sessions

    if status:
        try:
            status_enum = SessionStatus(status)
            sessions = [s for s in sessions if s.status == status_enum]
        except ValueError:
            pass

    return SessionListResponse(
        sessions=[session_response(s) for s in sessions],
        total=len(sessions),
    )


@router.get("/", response_model=SessionListResponse)
async def list_sessions_route(
    status: str | None = None,
    thread_id: str | None = None,
) -> SessionListResponse:
    """List sessions, optionally filtered by status and/or thread id."""
    return await list_sessions(status=status, thread_id=thread_id)


async def get_session(session_id: str) -> SessionResponse:
    """Return the current snapshot of a session."""
    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)
    return session_response(session)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session_route(session_id: str) -> SessionResponse:
    """Return the current snapshot of a session."""
    return await get_session(session_id)


async def get_session_events(
    session_id: str,
    last_event_id: str | None = None,
) -> EventSourceResponse:
    """Open an SSE stream for the session, replaying from ``last_event_id``."""
    manager = get_session_manager()
    _ = get_session_or_404(session_id, manager=manager)

    bridge = get_event_bridge(session_id)
    if bridge is None:
        bridge = create_event_bridge(session_id)

    return EventSourceResponse(bridge.generate_sse(last_event_id=last_event_id))


@router.get("/{session_id}/events")
async def get_session_events_route(
    session_id: str,
    last_event_id: str | None = None,
) -> EventSourceResponse:
    """Open an SSE stream for the session, replaying from ``last_event_id``."""
    return await get_session_events(session_id, last_event_id=last_event_id)


async def get_session_history(session_id: str) -> dict[str, object]:
    """Return the captured event history for the session."""
    manager = get_session_manager()
    _ = get_session_or_404(session_id, manager=manager)

    bridge = get_event_bridge(session_id)
    events = bridge.get_history() if bridge else []

    return {
        "session_id": session_id,
        "events": events,
        "total": len(events),
    }


@router.get("/{session_id}/history")
async def get_session_history_route(session_id: str) -> dict[str, object]:
    """Return the captured event history for the session."""
    return await get_session_history(session_id)
