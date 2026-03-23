"""Lifecycle helpers for session management."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from maivn_studio.config.models import DemoConfig

from ..demo_loader.loader import get_demo_loader
from ..event_bridge import remove_event_bridge
from .messages import apply_turn_configuration
from .models import SessionStatus, StudioSession
from .private_data import apply_private_data

# MARK: Resource Cleanup


def close_scope_resources(scope: Any) -> None:
    """Close an executor/agent/swarm scope if it exposes cleanup APIs."""
    close_fn = getattr(scope, "close", None)
    if callable(close_fn):
        try:
            close_fn()
        except Exception:
            pass
        return

    close_mcp_servers = getattr(scope, "close_mcp_servers", None)
    if callable(close_mcp_servers):
        try:
            close_mcp_servers()
        except Exception:
            pass


def release_loaded_demo(session: StudioSession) -> None:
    """Release resources associated with a loaded demo."""
    loaded = session._loaded_demo
    if loaded is None:
        return

    seen: set[int] = set()
    scopes = [loaded.executor, *loaded.agents, *loaded.swarms]
    for scope in scopes:
        if scope is None:
            continue
        scope_id = id(scope)
        if scope_id in seen:
            continue
        seen.add(scope_id)
        close_scope_resources(scope)

    session._loaded_demo = None


async def shutdown_sessions(sessions: list[StudioSession]) -> None:
    """Cancel all running sessions and release associated resources."""
    for session in sessions:
        task = session._task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
        session._task = None

    for session in sessions:
        release_loaded_demo(session)

    for session in sessions:
        remove_event_bridge(session.session_id)


# MARK: Session Lifecycle


async def create_session_record(
    *,
    sessions: dict[str, StudioSession],
    sessions_by_thread: dict[str, list[str]],
    demo_config: DemoConfig,
    variant: str | None,
    thread_id: str | None,
    metadata: dict[str, Any] | None,
    private_data: dict[str, Any] | None,
) -> StudioSession:
    """Create and register a new session record."""
    session_id = str(uuid.uuid4())
    resolved_thread_id = thread_id or str(uuid.uuid4())

    session_metadata = metadata or {}
    if private_data:
        session_metadata["user_private_data"] = private_data

    session = StudioSession(
        session_id=session_id,
        demo_config=demo_config,
        thread_id=resolved_thread_id,
        variant=variant,
        metadata=session_metadata,
    )

    sessions[session_id] = session
    sessions_by_thread.setdefault(resolved_thread_id, []).append(session_id)
    return session


async def start_session_execution(
    manager: Any,
    session: StudioSession,
    *,
    message: str,
    message_type: str,
    system_message: str | None,
    attachments: list[dict[str, Any]] | None,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
) -> None:
    """Load a demo, initialize the session state, and launch execution."""
    if session.status != SessionStatus.CREATED:
        raise ValueError(f"Session {session.session_id} already started")

    loader = get_demo_loader()
    loaded = loader.load(session.demo_config, force_reload=True, variant=session.variant)
    session._loaded_demo = loaded

    user_private_data = session.metadata.get("user_private_data", {})
    apply_private_data(loaded, user_private_data)

    if not loaded.has_executor:
        session.status = SessionStatus.FAILED
        session.error = "Demo has no executable agent or swarm"
        return

    apply_turn_configuration(
        session,
        structured_output=structured_output,
        invocation_kwargs=invocation_kwargs,
    )

    if system_message:
        session.messages.append(SystemMessage(content=system_message))

    session.messages.append(manager._create_message(message, message_type, attachments=attachments))
    session.status = SessionStatus.RUNNING
    session.started_at = datetime.now()
    session._task = asyncio.create_task(
        manager._execute_session(session),
        name=f"session-{session.session_id}",
    )


async def send_followup_message(
    manager: Any,
    session: StudioSession,
    *,
    message: str,
    message_type: str,
    attachments: list[dict[str, Any]] | None,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
) -> None:
    """Queue or start a follow-up message for an existing session."""
    if session.can_stage_message:
        manager._enqueue_message(
            session,
            message=message,
            message_type=message_type,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
        )
        return

    if not session.can_send_message:
        raise ValueError(
            f"Session {session.session_id} not ready for messages (status: {session.status.value})"
        )

    apply_turn_configuration(
        session,
        structured_output=structured_output,
        invocation_kwargs=invocation_kwargs,
    )

    session.messages.append(manager._create_message(message, message_type, attachments=attachments))
    session.status = SessionStatus.RUNNING
    session._task = asyncio.create_task(
        manager._execute_session(session),
        name=f"session-{session.session_id}",
    )


async def submit_interrupt_response(
    session: StudioSession,
    *,
    data_key: str,
    value: Any,
) -> None:
    """Store an interrupt response so the current run can resume.

    Interrupted turns can surface as ``READY`` at the Studio layer because the
    underlying SDK stream emits a terminal payload before the reporter-backed
    interrupt is resolved. Accept ``READY`` here so the submit API can move the
    session back to ``RUNNING`` while the checkpoint resume continues.
    """
    if session.status not in (
        SessionStatus.RUNNING,
        SessionStatus.WAITING_INPUT,
        SessionStatus.READY,
    ):
        raise ValueError(f"Session {session.session_id} not accepting interrupts")

    if "interrupt_responses" not in session.metadata:
        session.metadata["interrupt_responses"] = {}
    session.metadata["interrupt_responses"][data_key] = value
    session.status = SessionStatus.RUNNING


async def end_session_record(manager: Any, session: StudioSession) -> None:
    """End a session and emit the terminal event."""
    if not session.is_active:
        return

    if session._task and not session._task.done():
        session._task.cancel()
        try:
            await session._task
        except asyncio.CancelledError:
            pass

    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.now()
    session._task = None

    await manager._emit_event(
        session,
        "session_end",
        {
            "session_id": session.session_id,
            "total_turns": len([m for m in session.messages if isinstance(m, HumanMessage)]),
        },
    )

    release_loaded_demo(session)


async def cancel_session_record(session: StudioSession) -> None:
    """Cancel a running session and release resources."""
    if session._task and not session._task.done():
        session._task.cancel()
        try:
            await session._task
        except asyncio.CancelledError:
            pass

    session.status = SessionStatus.CANCELLED
    session.completed_at = datetime.now()
    session._task = None
    release_loaded_demo(session)
