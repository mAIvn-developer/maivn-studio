"""Route handlers for session management."""

from __future__ import annotations

from fastapi import APIRouter

from .models import SessionListResponse, SessionResponse
from .reads import list_sessions_route
from .reads import router as reads_router
from .writes import create_session_route
from .writes import router as writes_router

router = APIRouter(prefix="/api/sessions", tags=["sessions"])

# Keep both root path variants: ``add_api_route('')`` serves ``/api/sessions``,
# while the included routers keep ``/api/sessions/`` via their ``'/'`` decorators.
router.add_api_route("", list_sessions_route, methods=["GET"], response_model=SessionListResponse)
router.add_api_route(
    "",
    create_session_route,
    methods=["POST"],
    response_model=SessionResponse,
)

router.include_router(reads_router)
router.include_router(writes_router)
