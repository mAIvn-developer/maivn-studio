# pyright: strict
"""Lifecycle helpers for session management."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from maivn_studio.config.models import AppConfig

from ..app_loader.loader import get_app_loader
from ..app_loader.models import LoadedApp
from ..event_bridge import remove_event_bridge
from .messages import apply_turn_configuration
from .models import SessionStatus, StudioSession
from .private_data import apply_private_data
from .protocols import Executor, SessionManagerLike

# MARK: Resource Cleanup


def close_loaded_app_resources(session: StudioSession) -> None:
    """Close loaded app executors during process-level shutdown."""
    loaded_app = session.loaded_app
    if loaded_app is None:
        return

    seen: set[int] = set()
    for resource in _iter_loaded_app_resources(loaded_app):
        resource_id = id(resource)
        if resource_id in seen:
            continue
        seen.add(resource_id)

        # Duck-type ``close()``: ``Agent`` exposes it, ``Swarm`` does not, and
        # tests pass lightweight closeable stubs. Skip anything not closeable.
        close: object = getattr(resource, "close", None)
        if not callable(close):
            continue
        try:
            _ = close()
        except Exception:  # noqa: BLE001 - resource close() should never block shutdown
            pass


def _iter_loaded_app_resources(loaded_app: LoadedApp) -> list[Executor]:
    resources: list[Executor] = []
    executor = loaded_app.executor
    if executor is not None:
        resources.append(executor)

    resources.extend(loaded_app.swarms)
    resources.extend(loaded_app.agents)

    for swarm in loaded_app.swarms:
        resources.extend(swarm.agents)

    return resources


def release_loaded_app(session: StudioSession) -> None:
    """Drop the session's reference to its loaded app.

    Historically this also called ``close()`` on the app's executor /
    agents / swarms. That broke apps whose ``Agent`` is a module-level
    singleton in a submodule - e.g. ``apps/projects/email_project/
    agent.py`` exporting ``agent = Agent(...)`` that the leaf app
    module picks up via ``from .agent import agent``. On the next
    session, ``AppLoader`` calls ``importlib.reload`` on the LEAF
    module only; the submodule stays cached, so ``loaded.agents`` on
    the new run resolves back to the SAME (now-closed) ``Agent``
    instance. The first tool dispatch then raised
    ``cannot schedule new futures after shutdown`` because the
    ``BackgroundExecutor`` attached to that shared Agent had already
    been torn down by the previous session's cleanup.

    Fix: the ``AppLoader`` does not create the Agent / Swarm objects -
    it discovers module-level globals via ``dir()`` - so Studio must
    not close them. Their lifecycle belongs to the app authors
    (typically "live for the process lifetime"). If an app truly does
    need per-run cleanup, GC will handle it when the reloaded module
    replaces the global and the old instance becomes unreachable
    (Agent.__del__ -> close()).

    Defense-in-depth at the SDK layer:
    ``libraries/maivn/.../background_executor.py`` now revives a shut-
    down pool on the next ``submit()``, so a previous version's
    ``close()`` can no longer brick a cached Agent.
    """
    if session.loaded_app is None:
        return
    session.loaded_app = None


async def shutdown_sessions(sessions: list[StudioSession]) -> None:
    """Cancel all running sessions and release associated resources."""
    for session in sessions:
        task = session.task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception:  # noqa: BLE001 - shutdown must drain tasks even if they erred
                pass
        session.task = None

    for session in sessions:
        close_loaded_app_resources(session)
        release_loaded_app(session)

    for session in sessions:
        remove_event_bridge(session.session_id)


# MARK: Session Lifecycle


async def create_session_record(
    *,
    sessions: dict[str, StudioSession],
    sessions_by_thread: dict[str, list[str]],
    app_config: AppConfig,
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
        app_config=app_config,
        thread_id=resolved_thread_id,
        variant=variant,
        metadata=session_metadata,
    )

    sessions[session_id] = session
    sessions_by_thread.setdefault(resolved_thread_id, []).append(session_id)
    return session


async def start_session_execution(
    manager: SessionManagerLike,
    session: StudioSession,
    *,
    message: str,
    message_type: str,
    system_message: str | None,
    attachments: list[dict[str, Any]] | None,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
    batch_config: dict[str, Any] | None,
) -> None:
    """Load an app, initialize the session state, and launch execution."""
    if session.status != SessionStatus.CREATED:
        raise ValueError(f"Session {session.session_id} already started")

    loader = get_app_loader()
    loaded = loader.load(session.app_config, force_reload=True, variant=session.variant)
    session.loaded_app = loaded

    user_private_data = session.metadata.get("user_private_data", {})
    apply_private_data(loaded, user_private_data)

    if not loaded.has_executor:
        session.status = SessionStatus.FAILED
        session.error = "App has no executable agent or swarm"
        return

    apply_turn_configuration(
        session,
        structured_output=structured_output,
        invocation_kwargs=invocation_kwargs,
        batch_config=batch_config,
    )

    if system_message:
        session.messages.append(SystemMessage(content=system_message))

    session.messages.append(manager.create_message(message, message_type, attachments=attachments))
    session.status = SessionStatus.RUNNING
    session.started_at = datetime.now()
    session.task = asyncio.create_task(
        manager.run_session(session),
        name=f"session-{session.session_id}",
    )


async def send_followup_message(
    manager: SessionManagerLike,
    session: StudioSession,
    *,
    message: str,
    message_type: str,
    attachments: list[dict[str, Any]] | None,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
    batch_config: dict[str, Any] | None,
) -> None:
    """Queue or start a follow-up message for an existing session."""
    if session.can_stage_message:
        manager.enqueue_message(
            session,
            message=message,
            message_type=message_type,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
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
        batch_config=batch_config,
    )

    session.messages.append(manager.create_message(message, message_type, attachments=attachments))
    session.status = SessionStatus.RUNNING
    session.task = asyncio.create_task(
        manager.run_session(session),
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

    interrupt_responses: dict[str, Any] = session.metadata.get("interrupt_responses") or {}
    interrupt_responses[data_key] = value
    session.metadata["interrupt_responses"] = interrupt_responses
    session.status = SessionStatus.RUNNING


async def end_session_record(manager: SessionManagerLike, session: StudioSession) -> None:
    """End a session and emit the terminal event."""
    if not session.is_active:
        return

    task = session.task
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.now()
    session.task = None

    await manager.emit_event(
        session,
        "session_end",
        {
            "session_id": session.session_id,
            "total_turns": len([m for m in session.messages if isinstance(m, HumanMessage)]),
        },
    )

    release_loaded_app(session)


async def cancel_session_record(session: StudioSession) -> None:
    """Cancel a running session and release resources."""
    task = session.task
    if task and not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    session.status = SessionStatus.CANCELLED
    session.completed_at = datetime.now()
    session.task = None
    release_loaded_app(session)
