# pyright: strict
from __future__ import annotations

from typing import cast

import pytest

from maivn_studio.services.event_bridge import MAX_EVENT_HISTORY, EventBridge


def _event_data(event: dict[str, object]) -> dict[str, object]:
    """Return an event's ``data`` payload narrowed to ``dict[str, object]``."""
    data = event["data"]
    assert isinstance(data, dict)
    return cast("dict[str, object]", data)


@pytest.mark.asyncio
async def test_event_history_is_capped() -> None:
    bridge = EventBridge("session-1")

    for idx in range(MAX_EVENT_HISTORY + 5):
        await bridge.emit("event", {"i": idx})

    history = bridge.get_history()

    assert len(history) == MAX_EVENT_HISTORY
    assert _event_data(history[0])["i"] == 5


@pytest.mark.asyncio
async def test_emit_assistant_chunk_records_event() -> None:
    bridge = EventBridge("session-2")

    await bridge.emit_assistant_chunk(assistant_id="orchestrator_agent", text="hello")

    history = bridge.get_history()
    assert len(history) == 1
    assert history[0]["type"] == "assistant_chunk"
    assert _event_data(history[0])["assistant_id"] == "orchestrator_agent"
    assert _event_data(history[0])["text"] == "hello"
