# pyright: strict
"""Event bridge for streaming SDK events to UI via SSE.

Studio uses :class:`maivn.events.EventBridge` directly. Both interrupt
dedup (default) and adjacent-status_message dedup are turned on, since
both StudioReporter and the contract-stream replay can surface the same
logical event through different paths.
"""

from __future__ import annotations

from maivn.events import BridgeRegistry, EventBridge, UIEvent
from maivn.events._bridge import safe_json_dumps

# Default max history from the EventBridge constructor.
MAX_EVENT_HISTORY = 500


# MARK: Registry


def _studio_bridge_factory(session_id: str) -> EventBridge:
    return EventBridge(
        session_id,
        audience="internal",
        dedupe_status_messages=True,
    )


_registry = BridgeRegistry()


def create_event_bridge(session_id: str) -> EventBridge:
    """Create a Studio-configured event bridge."""
    return _registry.create(session_id, factory=_studio_bridge_factory)


def get_event_bridge(session_id: str) -> EventBridge | None:
    """Return the registered bridge for a session, or ``None``."""
    return _registry.get(session_id)


def remove_event_bridge(session_id: str) -> None:
    """Remove and close the registered bridge for a session."""
    _registry.remove(session_id)


def clear_event_bridges() -> None:
    """Close and drop every registered bridge.

    Test-only reset seam. Delegates to the SDK ``BridgeRegistry.clear()``,
    which closes every bridge before emptying the registry.
    """
    _registry.clear()


__all__ = [
    "EventBridge",
    "MAX_EVENT_HISTORY",
    "UIEvent",
    "clear_event_bridges",
    "create_event_bridge",
    "get_event_bridge",
    "remove_event_bridge",
    "safe_json_dumps",
]
