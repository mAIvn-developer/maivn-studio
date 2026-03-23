"""Interrupt registry for coordinating UI input collection."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


# MARK: Registry State

# Global registry for pending interrupts
# Maps interrupt_id -> (threading.Event, response_value, aliases)
_pending_interrupts: dict[str, tuple[threading.Event, list[str], set[str]]] = {}
_interrupt_aliases: dict[str, str] = {}
_interrupt_lock = threading.Lock()


# MARK: Public API


def _normalize_interrupt_key(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_interrupt_id(interrupt_id: str) -> str | None:
    normalized = _normalize_interrupt_key(interrupt_id)
    if normalized is None:
        return None
    return _interrupt_aliases.get(
        normalized, normalized if normalized in _pending_interrupts else None
    )


def register_interrupt(
    interrupt_id: str,
    *,
    aliases: list[str] | None = None,
) -> threading.Event:
    """Register a pending interrupt and return an event to wait on."""
    event = threading.Event()
    normalized_aliases = {
        alias
        for raw_alias in aliases or []
        if (alias := _normalize_interrupt_key(raw_alias)) is not None and alias != interrupt_id
    }
    with _interrupt_lock:
        _pending_interrupts[interrupt_id] = (event, [], normalized_aliases)
        _interrupt_aliases[interrupt_id] = interrupt_id
        for alias in normalized_aliases:
            _interrupt_aliases[alias] = interrupt_id
    return event


def resolve_interrupt(interrupt_id: str, value: str) -> bool:
    """Resolve a pending interrupt with the provided value."""
    with _interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            logger.warning(f"Interrupt {interrupt_id} not found in pending interrupts")
            return False
        event, response_list, _ = _pending_interrupts[resolved_interrupt_id]
        response_list.append(value)
        event.set()
        return True


def get_interrupt_response(interrupt_id: str) -> str | None:
    """Get the response for a resolved interrupt."""
    with _interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            return None
        _, response_list, _ = _pending_interrupts[resolved_interrupt_id]
        return response_list[0] if response_list else None


def cleanup_interrupt(interrupt_id: str) -> None:
    """Clean up a completed interrupt."""
    with _interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            return

        _, _, aliases = _pending_interrupts.pop(resolved_interrupt_id, (None, [], set()))
        _interrupt_aliases.pop(resolved_interrupt_id, None)
        for alias in aliases:
            if _interrupt_aliases.get(alias) == resolved_interrupt_id:
                _interrupt_aliases.pop(alias, None)
