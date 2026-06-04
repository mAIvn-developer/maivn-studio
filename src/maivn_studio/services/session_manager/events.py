# pyright: strict
"""Event helpers for session management."""

from __future__ import annotations

import logging
from typing import Any

from .models import StudioSession
from .protocols import Executor, SessionManagerLike

# MARK: Session Events


async def emit_session_start_event(
    manager: SessionManagerLike,
    session: StudioSession,
    *,
    executor: Executor,
    executor_type: str,
    consumed_queued_message_count: int = 0,
) -> None:
    """Emit a session_start SSE event with queue telemetry."""
    structured_output_config = session.metadata.get("structured_output")
    batch_config = session.metadata.get("batch_config")
    await manager.emit_event(
        session,
        "session_start",
        {
            "session_id": session.session_id,
            "app_id": session.app_config.id,
            "executor_type": executor_type,
            "executor_name": executor.name,
            "structured_output": structured_output_config is not None,
            "batch": isinstance(batch_config, dict),
            "queued_message_count": session.queued_message_count,
            "consumed_queued_message_count": consumed_queued_message_count,
        },
    )


async def emit_event(
    session: StudioSession,
    event_type: str,
    data: dict[str, Any],
    *,
    logger: logging.Logger,
) -> None:
    """Emit an event to the session's event bridge for SSE streaming."""
    from ..event_bridge import create_event_bridge, get_event_bridge

    bridge = get_event_bridge(session.session_id)
    if bridge is None:
        bridge = create_event_bridge(session.session_id)
    if bridge:
        await bridge.emit(event_type, data)
    else:
        logger.warning("No event bridge for session %s", session.session_id)
