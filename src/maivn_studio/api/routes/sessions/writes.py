# pyright: strict

from __future__ import annotations

import logging
from typing import cast

from fastapi import APIRouter, HTTPException

from maivn_studio.config.models import AppConfig
from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.event_bridge import create_event_bridge
from maivn_studio.services.session_manager.manager import get_session_manager

from .helpers import (
    build_batch_config,
    build_invocation_kwargs,
    build_structured_output_config,
    get_session_or_404,
    merge_private_data,
    refresh_registry_from_disk,
    serialize_attachments,
    session_response,
)
from .models import (
    CreateSessionRequest,
    SendMessageRequest,
    SessionResponse,
    SubmitInterruptRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _request_event_subscriber_wait(session: object) -> None:
    # ``session`` is a ``StudioSession`` in production, but tests pass lightweight
    # doubles that may lack ``metadata``; keep the defensive guard so the route
    # tolerates off-contract objects (see typecheck-strict-policy defensive guard).
    metadata = getattr(session, "metadata", None)
    if isinstance(metadata, dict):
        metadata = cast("dict[str, object]", metadata)
        metadata["_wait_for_event_subscriber"] = True


def _resolve_app_variant(app: AppConfig, requested_variant: str | None) -> str | None:
    """Resolve the effective session variant, falling back to the app default."""
    if requested_variant:
        return requested_variant

    default_variant = app.default_variant
    if not default_variant or not default_variant.strip():
        return None

    normalized_variant = default_variant.strip()
    if normalized_variant in app.variants:
        return normalized_variant

    logger.warning(
        "Ignoring invalid default variant %r for app %s; available variants: %s",
        normalized_variant,
        app.id,
        sorted(app.variants.keys()),
    )
    return None


async def create_session(request: CreateSessionRequest) -> SessionResponse:
    """Create a session for an app + variant and dispatch the initial message."""
    refresh_registry_from_disk()

    registry = get_registry()
    app = registry.get(request.app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {request.app_id}")

    if request.variant and request.variant not in app.variants:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid variant: {request.variant}. Available: {list(app.variants.keys())}",
        )

    resolved_variant = _resolve_app_variant(app, request.variant)
    variant_private_data = None
    if resolved_variant is not None:
        variant_private_data = app.variants[resolved_variant].private_data

    manager = get_session_manager()
    session = await manager.create_session(
        app_config=app,
        variant=resolved_variant,
        thread_id=request.thread_id,
        private_data=merge_private_data(
            app.private_data,
            variant_private_data,
            request.private_data,
        ),
    )

    _ = create_event_bridge(session.session_id)
    _request_event_subscriber_wait(session)

    structured_output_config = build_structured_output_config(request.structured_output)
    invocation_kwargs = build_invocation_kwargs(request.invocation)
    attachments = serialize_attachments(request.attachments)
    batch_config = build_batch_config(
        request.batch,
        message_type=request.message_type,
        attachments=attachments,
    )

    try:
        await manager.start_session(
            session,
            request.message,
            message_type=request.message_type,
            system_message=request.system_message,
            attachments=attachments,
            structured_output=structured_output_config,
            invocation_kwargs=invocation_kwargs or None,
            batch_config=batch_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return session_response(session)


@router.post("/", response_model=SessionResponse, include_in_schema=False)
async def create_session_route(request: CreateSessionRequest) -> SessionResponse:
    """Create a session for an app + variant and dispatch the initial message."""
    return await create_session(request)


async def send_message(session_id: str, request: SendMessageRequest) -> SessionResponse:
    """Send a follow-up message into an active session."""
    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)

    if not session.can_send_message and not session.can_stage_message:
        raise HTTPException(
            status_code=400,
            detail=f"Session cannot accept messages. Status: {session.status.value}",
        )

    structured_output_config = build_structured_output_config(request.structured_output)
    invocation_kwargs = build_invocation_kwargs(request.invocation)
    attachments = serialize_attachments(request.attachments)
    batch_config = build_batch_config(
        request.batch,
        message_type=request.message_type,
        attachments=attachments,
    )
    _request_event_subscriber_wait(session)

    try:
        await manager.send_message(
            session,
            request.message,
            message_type=request.message_type,
            attachments=attachments,
            structured_output=structured_output_config,
            invocation_kwargs=invocation_kwargs or None,
            batch_config=batch_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return session_response(session)


@router.post("/{session_id}/messages", response_model=SessionResponse)
async def send_message_route(session_id: str, request: SendMessageRequest) -> SessionResponse:
    """Send a follow-up message into an active session."""
    return await send_message(session_id, request)


async def submit_interrupt(
    session_id: str,
    request: SubmitInterruptRequest,
) -> SessionResponse:
    """Resolve a pending interrupt request with a user-supplied value."""
    from maivn_studio.services.studio_reporter.interrupts import resolve_interrupt

    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)

    resolve_candidates = [request.interrupt_id]
    if request.data_key:
        resolve_candidates.append(f"{session_id}:{request.data_key}")
    unique_candidates = [
        candidate
        for i, candidate in enumerate(resolve_candidates)
        if candidate and candidate not in resolve_candidates[:i]
    ]

    resolved = False
    for resolve_id in unique_candidates:
        if resolve_interrupt(resolve_id, str(request.value)):
            resolved = True
            break

    if not resolved:
        msg = (
            "Interrupt candidates %s not found for session %s,"
            + " they may have already been resolved or timed out"
        )
        logger.warning(msg, unique_candidates, session_id)

    try:
        await manager.submit_interrupt(session, request.data_key, request.value)
    except ValueError as exc:
        logger.warning(
            "Submit interrupt ignored for session %s (status=%s): %s",
            session_id,
            session.status.value,
            exc,
        )

    return session_response(session)


@router.post("/{session_id}/interrupt", response_model=SessionResponse)
async def submit_interrupt_route(
    session_id: str,
    request: SubmitInterruptRequest,
) -> SessionResponse:
    """Resolve a pending interrupt request with a user-supplied value."""
    return await submit_interrupt(session_id, request)


async def end_session(session_id: str) -> SessionResponse:
    """End the session gracefully and return its final snapshot."""
    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)
    await manager.end_session(session)
    return session_response(session)


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session_route(session_id: str) -> SessionResponse:
    """End the session gracefully and return its final snapshot."""
    return await end_session(session_id)


async def cancel_session_compat(session_id: str) -> SessionResponse:
    """Cancel the session (POST compat path used by older clients)."""
    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)
    await manager.cancel_session(session)
    return session_response(session)


@router.post("/{session_id}/cancel", response_model=SessionResponse)
async def cancel_session_compat_route(session_id: str) -> SessionResponse:
    """Cancel the session (POST compat path used by older clients)."""
    return await cancel_session_compat(session_id)


async def cancel_session(session_id: str) -> SessionResponse:
    """Cancel the session and return its final snapshot."""
    manager = get_session_manager()
    session = get_session_or_404(session_id, manager=manager)
    await manager.cancel_session(session)
    return session_response(session)


@router.delete("/{session_id}", response_model=SessionResponse)
async def cancel_session_route(session_id: str) -> SessionResponse:
    """Cancel the session and return its final snapshot."""
    return await cancel_session(session_id)
