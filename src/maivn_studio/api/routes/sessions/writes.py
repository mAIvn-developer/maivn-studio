from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.event_bridge import create_event_bridge
from maivn_studio.services.session_manager.manager import get_session_manager

from .helpers import (
    _build_batch_config,
    _build_invocation_kwargs,
    _build_structured_output_config,
    _get_session_or_404,
    _merge_private_data,
    _refresh_registry_from_disk,
    _serialize_attachments,
)
from .models import (
    CreateSessionRequest,
    SendMessageRequest,
    SessionResponse,
    SubmitInterruptRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def _resolve_demo_variant(demo, requested_variant: str | None) -> str | None:
    """Resolve the effective session variant, falling back to the demo default."""
    if requested_variant:
        return requested_variant

    default_variant = getattr(demo, "default_variant", None)
    if not isinstance(default_variant, str) or not default_variant.strip():
        return None

    normalized_variant = default_variant.strip()
    if normalized_variant in demo.variants:
        return normalized_variant

    logger.warning(
        "Ignoring invalid default variant %r for demo %s; available variants: %s",
        normalized_variant,
        demo.id,
        sorted(demo.variants.keys()),
    )
    return None


async def create_session(request: CreateSessionRequest) -> SessionResponse:
    _refresh_registry_from_disk()

    registry = get_registry()
    demo = registry.get(request.demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {request.demo_id}")

    if request.variant and request.variant not in demo.variants:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid variant: {request.variant}. Available: {list(demo.variants.keys())}",
        )

    resolved_variant = _resolve_demo_variant(demo, request.variant)
    variant_private_data = None
    if resolved_variant is not None:
        variant_private_data = demo.variants[resolved_variant].private_data

    manager = get_session_manager()
    session = await manager.create_session(
        demo_config=demo,
        variant=resolved_variant,
        thread_id=request.thread_id,
        private_data=_merge_private_data(
            demo.private_data,
            variant_private_data,
            request.private_data,
        ),
    )

    create_event_bridge(session.session_id)

    structured_output_config = _build_structured_output_config(request.structured_output)
    invocation_kwargs = _build_invocation_kwargs(request.invocation)
    attachments = _serialize_attachments(request.attachments)
    batch_config = _build_batch_config(
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

    return SessionResponse(**session.to_dict())


@router.post("/", response_model=SessionResponse, include_in_schema=False)
async def create_session_route(request: CreateSessionRequest) -> SessionResponse:
    return await create_session(request)


async def send_message(session_id: str, request: SendMessageRequest) -> SessionResponse:
    manager = get_session_manager()
    session = _get_session_or_404(session_id, manager=manager)

    if not session.can_send_message and not session.can_stage_message:
        raise HTTPException(
            status_code=400,
            detail=f"Session cannot accept messages. Status: {session.status.value}",
        )

    structured_output_config = _build_structured_output_config(request.structured_output)
    invocation_kwargs = _build_invocation_kwargs(request.invocation)
    attachments = _serialize_attachments(request.attachments)
    batch_config = _build_batch_config(
        request.batch,
        message_type=request.message_type,
        attachments=attachments,
    )

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

    return SessionResponse(**session.to_dict())


@router.post("/{session_id}/messages", response_model=SessionResponse)
async def send_message_route(session_id: str, request: SendMessageRequest) -> SessionResponse:
    return await send_message(session_id, request)


async def submit_interrupt(
    session_id: str,
    request: SubmitInterruptRequest,
) -> SessionResponse:
    from maivn_studio.services.studio_reporter.interrupts import resolve_interrupt

    manager = get_session_manager()
    session = _get_session_or_404(session_id, manager=manager)

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
        logger.warning(
            "Interrupt candidates %s not found for session %s, "
            "they may have already been resolved or timed out",
            unique_candidates,
            session_id,
        )

    try:
        await manager.submit_interrupt(session, request.data_key, request.value)
    except ValueError as exc:
        logger.warning(
            "Submit interrupt ignored for session %s (status=%s): %s",
            session_id,
            session.status.value,
            exc,
        )

    return SessionResponse(**session.to_dict())


@router.post("/{session_id}/interrupt", response_model=SessionResponse)
async def submit_interrupt_route(
    session_id: str,
    request: SubmitInterruptRequest,
) -> SessionResponse:
    return await submit_interrupt(session_id, request)


async def end_session(session_id: str) -> SessionResponse:
    manager = get_session_manager()
    session = _get_session_or_404(session_id, manager=manager)
    await manager.end_session(session)
    return SessionResponse(**session.to_dict())


@router.post("/{session_id}/end", response_model=SessionResponse)
async def end_session_route(session_id: str) -> SessionResponse:
    return await end_session(session_id)


async def cancel_session_compat(session_id: str) -> SessionResponse:
    manager = get_session_manager()
    session = _get_session_or_404(session_id, manager=manager)
    await manager.cancel_session(session)
    return SessionResponse(**session.to_dict())


@router.post("/{session_id}/cancel", response_model=SessionResponse)
async def cancel_session_compat_route(session_id: str) -> SessionResponse:
    return await cancel_session_compat(session_id)


async def cancel_session(session_id: str) -> SessionResponse:
    manager = get_session_manager()
    session = _get_session_or_404(session_id, manager=manager)
    await manager.cancel_session(session)
    return SessionResponse(**session.to_dict())


@router.delete("/{session_id}", response_model=SessionResponse)
async def cancel_session_route(session_id: str) -> SessionResponse:
    return await cancel_session(session_id)
