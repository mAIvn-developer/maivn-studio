# pyright: strict
"""Interrupt registry for coordinating UI input collection."""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)


# MARK: Registry State

# Global registry for pending interrupts.
# Maps interrupt_id -> (threading.Event, response_value, aliases).
pending_interrupts: dict[str, tuple[threading.Event, list[str], set[str]]] = {}
interrupt_aliases: dict[str, str] = {}
interrupt_lock = threading.Lock()


# MARK: Internal Helpers


def _normalize_interrupt_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _resolve_interrupt_id(interrupt_id: str) -> str | None:
    normalized = _normalize_interrupt_key(interrupt_id)
    if normalized is None:
        return None
    return interrupt_aliases.get(
        normalized, normalized if normalized in pending_interrupts else None
    )


# MARK: Public API


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
    with interrupt_lock:
        pending_interrupts[interrupt_id] = (event, [], normalized_aliases)
        interrupt_aliases[interrupt_id] = interrupt_id
        for alias in normalized_aliases:
            interrupt_aliases[alias] = interrupt_id
    return event


def resolve_interrupt(interrupt_id: str, value: str) -> bool:
    """Resolve a pending interrupt with the provided value."""
    with interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            logger.warning(f"Interrupt {interrupt_id} not found in pending interrupts")
            return False
        event, response_list, _ = pending_interrupts[resolved_interrupt_id]
        response_list.append(value)
        event.set()
        return True


def get_interrupt_response(interrupt_id: str) -> str | None:
    """Get the response for a resolved interrupt."""
    with interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            return None
        _, response_list, _ = pending_interrupts[resolved_interrupt_id]
        return response_list[0] if response_list else None


def cleanup_interrupt(interrupt_id: str) -> None:
    """Clean up a completed interrupt."""
    with interrupt_lock:
        resolved_interrupt_id = _resolve_interrupt_id(interrupt_id)
        if resolved_interrupt_id is None:
            return

        _, _, aliases = pending_interrupts.pop(
            resolved_interrupt_id, (threading.Event(), [], set())
        )
        _ = interrupt_aliases.pop(resolved_interrupt_id, None)
        for alias in aliases:
            if interrupt_aliases.get(alias) == resolved_interrupt_id:
                _ = interrupt_aliases.pop(alias, None)


__all__ = [
    "cleanup_interrupt",
    "get_interrupt_response",
    "interrupt_aliases",
    "interrupt_lock",
    "pending_interrupts",
    "register_interrupt",
    "resolve_interrupt",
]
