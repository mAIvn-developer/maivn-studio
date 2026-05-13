"""Capability detection, reporter flushing, and stream-tool contract maps.

Small helpers that the session-execution code uses across both invoke and
stream paths. Kept here so the orchestration module can stay focused on the
turn loop.
"""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, cast

from ..models import StudioSession

# Give the frontend a chance to open EventSource after the create/send POST
# returns. If no UI subscribes, execution still proceeds quickly for API users.
_FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS = 1.0

# MARK: Capability Helpers


def supports_structured_output_kwarg(executor: Any) -> bool:
    """Return whether the executor accepts a structured_output invoke kwarg."""
    invoke_fn = getattr(executor, "invoke", None)
    if not callable(invoke_fn):
        return False
    try:
        params = inspect.signature(invoke_fn).parameters
    except (TypeError, ValueError):
        return False

    if "structured_output" in params:
        return True

    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())


async def flush_reporter_events(reporter: Any | None, logger: Any) -> None:
    """Flush buffered reporter output if supported."""
    flush_fn = getattr(reporter, "flush", None)
    if not callable(flush_fn):
        return
    try:
        flush_result = flush_fn()
        if inspect.isawaitable(flush_result):
            await flush_result
    except Exception as exc:  # noqa: BLE001 - flushing must never abort a session
        logger.warning("Failed to flush pending Studio reporter events: %s", exc)


async def wait_for_event_subscriber(
    *,
    session: StudioSession,
    bridge: Any | None,
    logger: Any,
) -> None:
    """Wait briefly for the first UI event subscriber when requested."""
    if not session.metadata.pop("_wait_for_event_subscriber", False):
        return
    wait_for_subscriber = getattr(bridge, "wait_for_subscriber", None)
    if not callable(wait_for_subscriber):
        return
    wait_for_subscriber_fn = cast(Callable[..., Awaitable[bool]], wait_for_subscriber)
    try:
        subscribed = await wait_for_subscriber_fn(timeout=_FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS)
    except Exception as exc:  # noqa: BLE001 - subscriber wait is best-effort
        logger.debug(
            "Session %s: subscriber wait skipped after bridge error: %s",
            session.session_id,
            exc,
        )
        return
    if not subscribed:
        logger.debug(
            "Session %s: no SSE subscriber connected within %.2fs; starting anyway",
            session.session_id,
            _FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS,
        )


# MARK: Stream Tool Contract


def build_stream_tool_contract_maps(
    manager: Any,
    executor: Any,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    """Build tool name + metadata maps used when normalizing stream events.

    The session manager owns the canonical tool-contract maps; we extend them
    with whatever live tools the executor exposes so streaming events can be
    correlated even when the executor was rebuilt mid-turn.
    """
    tool_name_map, tool_metadata_map = manager._build_tool_contract_maps(executor)
    list_tools = getattr(executor, "list_tools", None)
    raw_tools_candidate = list_tools() if callable(list_tools) else []
    if isinstance(raw_tools_candidate, Iterable):
        raw_tools = list(raw_tools_candidate)
    else:
        raw_tools = []

    for tool in raw_tools:
        tool_name = getattr(tool, "name", None)
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue

        normalized_tool_name = tool_name.strip()
        tool_id = getattr(tool, "tool_id", None)
        if not isinstance(tool_id, str) or not tool_id.strip():
            tool_id = getattr(tool, "id", None)
        if not isinstance(tool_id, str) or not tool_id.strip():
            continue

        normalized_tool_id = tool_id.strip()
        metadata = tool_metadata_map.setdefault(
            normalized_tool_id, {"tool_name": normalized_tool_name}
        )
        metadata.setdefault("tool_name", normalized_tool_name)

        tool_type = getattr(tool, "tool_type", None)
        if not isinstance(tool_type, str) or not tool_type.strip():
            tool_type = getattr(tool, "type", None)
        if isinstance(tool_type, str) and tool_type.strip():
            metadata.setdefault("tool_type", tool_type.strip().lower())

        target_agent_id = getattr(tool, "target_agent_id", None)
        if isinstance(target_agent_id, str) and target_agent_id.strip():
            metadata.setdefault("target_agent_id", target_agent_id.strip())

        agent_name = getattr(tool, "agent_name", None)
        if isinstance(agent_name, str) and agent_name.strip():
            metadata.setdefault("agent_name", agent_name.strip())
        elif metadata.get("tool_type") == "agent":
            metadata.setdefault("agent_name", normalized_tool_name)

        swarm_name = getattr(tool, "swarm_name", None)
        if isinstance(swarm_name, str) and swarm_name.strip():
            metadata.setdefault("swarm_name", swarm_name.strip())

        tool_name_map.setdefault(normalized_tool_id, normalized_tool_name)

    return tool_name_map, tool_metadata_map


__all__ = [
    "_FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS",
    "build_stream_tool_contract_maps",
    "flush_reporter_events",
    "supports_structured_output_kwarg",
    "wait_for_event_subscriber",
]
