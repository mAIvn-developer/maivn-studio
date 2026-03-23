"""Event bridge for streaming SDK events to UI via SSE.

Thin wrapper around the shared ``maivn.events.EventBridge``. Studio keeps
the shared normalization, identity, replay, and security contract intact,
then adds a small app-specific duplicate-suppression layer for overlapping
delivery paths such as reporter-driven interrupts or repeated status
messages.
"""

from __future__ import annotations

from typing import Any

from maivn.events import BridgeRegistry, EventBridge, UIEvent
from maivn.events._bridge import safe_json_dumps

_safe_json_dumps = safe_json_dumps

# Default max history from the EventBridge constructor.
MAX_EVENT_HISTORY = 500


# MARK: Studio Bridge


def _normalize_interrupt_part(value: str | None) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip().lower()


def _build_interrupt_fingerprint(
    *,
    prompt: str,
    data_key: str,
    arg_name: str | None = None,
) -> tuple[str, str]:
    normalized_prompt = _normalize_interrupt_part(prompt)
    logical_key = _normalize_interrupt_part(arg_name) or _normalize_interrupt_part(data_key)
    return normalized_prompt, logical_key


class StudioEventBridge(EventBridge):
    """EventBridge with Studio-specific duplicate suppression.

    Both the StudioReporter (via ``get_input()``) and the contract-stream
    replay can emit the same logical interrupt to the bridge. Duplicate
    ``status_message`` emissions can also occur when the same
    status is surfaced through multiple reporting paths. This subclass
    tracks those cases and silently drops duplicates so the frontend only
    sees one logical update.
    """

    def __init__(self, session_id: str, **kwargs: Any) -> None:
        kwargs.setdefault("audience", "internal")
        super().__init__(session_id, **kwargs)
        self._emitted_interrupt_fingerprints: set[tuple[str, str]] = set()
        self._last_status_fingerprint: tuple[str, str] | None = None

    def _reset_turn_dedup_state(self) -> None:
        self._emitted_interrupt_fingerprints.clear()
        self._last_status_fingerprint = None

    @staticmethod
    def _build_status_fingerprint(data: dict[str, Any]) -> tuple[str, str] | None:
        message = data.get("message")
        if not isinstance(message, str):
            return None
        normalized_message = message.strip()
        if not normalized_message:
            return None

        assistant_id = data.get("assistant_id")
        normalized_assistant_id = (
            assistant_id.strip().lower()
            if isinstance(assistant_id, str) and assistant_id.strip()
            else ""
        )
        return normalized_assistant_id, normalized_message

    def _should_drop_status_message(self, data: dict[str, Any]) -> bool:
        fingerprint = self._build_status_fingerprint(data)
        if fingerprint is not None and fingerprint == self._last_status_fingerprint:
            return True
        self._last_status_fingerprint = fingerprint
        return False

    def _should_drop_interrupt(
        self,
        *,
        prompt: str,
        data_key: str,
        arg_name: str | None,
    ) -> bool:
        fingerprint = _build_interrupt_fingerprint(
            prompt=prompt,
            data_key=data_key,
            arg_name=arg_name,
        )
        if fingerprint in self._emitted_interrupt_fingerprints:
            return True
        self._emitted_interrupt_fingerprints.add(fingerprint)
        return False

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        # Reset per-turn interrupt dedup at the canonical turn boundary.
        # Studio sessions stay open across follow-up messages, so relying on
        # bridge.reopen() is insufficient because the bridge is not closed
        # between READY turns.
        if event_type == "session_start":
            self._reset_turn_dedup_state()

        if event_type == "status_message" and self._should_drop_status_message(data):
            return

        await super().emit(event_type, data)

    async def emit_interrupt_required(
        self,
        interrupt_id: str,
        data_key: str,
        prompt: str,
        arg_name: str | None = None,
        tool_name: str | None = None,
        checkpoint_id: str | None = None,
        assignment_id: str | None = None,
        interrupt_number: int = 1,
        total_interrupts: int = 1,
        input_type: str = "text",
        choices: list[str] | None = None,
    ) -> None:
        # Dedup by logical interrupt identity. The reporter path and the
        # contract-stream replay path can produce different interrupt IDs
        # for the same prompt/field pair.
        if self._should_drop_interrupt(
            prompt=prompt,
            data_key=data_key,
            arg_name=arg_name,
        ):
            return
        await super().emit_interrupt_required(
            interrupt_id=interrupt_id,
            data_key=data_key,
            prompt=prompt,
            arg_name=arg_name,
            tool_name=tool_name,
            checkpoint_id=checkpoint_id,
            assignment_id=assignment_id,
            interrupt_number=interrupt_number,
            total_interrupts=total_interrupts,
            input_type=input_type,
            choices=choices,
        )

    def reopen(self) -> None:
        """Reopen bridge for a new turn, clearing bridge and dedupe state."""
        super().reopen()
        self._reset_turn_dedup_state()


def _studio_bridge_factory(session_id: str) -> StudioEventBridge:
    return StudioEventBridge(session_id)


# MARK: Registry

_registry = BridgeRegistry()


def create_event_bridge(session_id: str) -> StudioEventBridge:
    """Create a Studio event bridge with interrupt dedup."""
    return _registry.create(session_id, factory=_studio_bridge_factory)  # type: ignore[return-value]


get_event_bridge = _registry.get
remove_event_bridge = _registry.remove

# Expose internal dict for test introspection.
_bridges = _registry._bridges

__all__ = [
    "EventBridge",
    "MAX_EVENT_HISTORY",
    "StudioEventBridge",
    "UIEvent",
    "_safe_json_dumps",
    "create_event_bridge",
    "get_event_bridge",
    "remove_event_bridge",
]
