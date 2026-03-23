from __future__ import annotations

import pytest

from maivn_studio.services.event_bridge import MAX_EVENT_HISTORY, EventBridge


@pytest.mark.asyncio
async def test_event_history_is_capped() -> None:
    bridge = EventBridge("session-1")

    for idx in range(MAX_EVENT_HISTORY + 5):
        await bridge.emit("event", {"i": idx})

    history = bridge.get_history()

    assert len(history) == MAX_EVENT_HISTORY
    assert history[0]["data"]["i"] == 5


@pytest.mark.asyncio
async def test_emit_assistant_chunk_records_event() -> None:
    bridge = EventBridge("session-2")

    await bridge.emit_assistant_chunk(assistant_id="orchestrator_agent", text="hello")

    history = bridge.get_history()
    assert len(history) == 1
    assert history[0]["type"] == "assistant_chunk"
    assert history[0]["data"]["assistant_id"] == "orchestrator_agent"
    assert history[0]["data"]["text"] == "hello"
