# pyright: strict
from __future__ import annotations

import asyncio
from typing import Any, cast

import pytest

from maivn_studio.services.event_bridge import EventBridge
from maivn_studio.services.studio_reporter.reporter import StudioReporter


def _data(event: dict[str, object]) -> dict[str, Any]:
    """Narrow an event's ``data`` payload (typed ``object`` by the SDK) to a dict."""
    return cast("dict[str, Any]", event["data"])


@pytest.mark.asyncio
async def test_studio_reporter_emits_assistant_chunk_deltas() -> None:
    bridge = EventBridge("session-reporter")
    reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())

    reporter.report_response_chunk(
        "Hello",
        assistant_id="orchestrator_agent",
        full_text="Hello",
    )
    await asyncio.sleep(0.05)

    reporter.report_response_chunk(
        " there",
        assistant_id="orchestrator_agent",
        full_text="Hello there",
    )
    await asyncio.sleep(0.05)

    # Duplicate full_text should not emit a new chunk.
    reporter.report_response_chunk(
        "",
        assistant_id="orchestrator_agent",
        full_text="Hello there",
    )
    await asyncio.sleep(0.05)

    history = bridge.get_history()
    assistant_chunks = [e for e in history if e.get("type") == "assistant_chunk"]

    assert [_data(e)["text"] for e in assistant_chunks] == ["Hello", " there"]


@pytest.mark.asyncio
async def test_studio_reporter_handles_diverged_assistant_snapshots() -> None:
    bridge = EventBridge("session-reporter")
    reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())

    reporter.report_response_chunk(
        "INVESTMENT MEMO: TechNova\\",
        assistant_id="agent-1",
        full_text="INVESTMENT MEMO: TechNova\\",
    )
    await asyncio.sleep(0.05)

    reporter.report_response_chunk(
        "\n\n## EXECUTIVE SUMMARY",
        assistant_id="agent-1",
        full_text="INVESTMENT MEMO: TechNova\n\n## EXECUTIVE SUMMARY",
    )
    await asyncio.sleep(0.05)

    history = bridge.get_history()
    assistant_chunks = [e for e in history if e.get("type") == "assistant_chunk"]

    # Diverged snapshot (snapshot 2 doesn't extend snapshot 1 as a strict
    # prefix — they share "INVESTMENT MEMO: TechNova" then diverge into
    # ``\\`` vs ``\n\n## EXECUTIVE SUMMARY``). The reporter now emits the
    # FULL cumulative text on the replace chunk (not just the divergent
    # suffix) so the UI overwrites the bubble with complete content rather
    # than a fragment, and tags the chunk with ``replace_content=True``.
    assert [_data(e)["text"] for e in assistant_chunks] == [
        "INVESTMENT MEMO: TechNova\\",
        "INVESTMENT MEMO: TechNova\n\n## EXECUTIVE SUMMARY",
    ]
    assert [_data(e).get("replace_content", False) for e in assistant_chunks] == [
        False,
        True,
    ]


@pytest.mark.asyncio
async def test_studio_reporter_emits_enrichment_with_memory_payload() -> None:
    bridge = EventBridge("session-reporter")
    reporter = StudioReporter(bridge=bridge, loop=asyncio.get_running_loop())

    reporter.report_enrichment(
        phase="memory_retrieved",
        message="Retrieved 5 memory hits",
        scope_id="orchestrator_agent",
        scope_name="orchestrator_agent",
        scope_type="agent",
        memory={
            "mode": "retrieve",
            "hit_count": 5,
            "latency_ms": 125,
        },
    )
    await asyncio.sleep(0.05)

    history = bridge.get_history()
    enrichment_events = [e for e in history if e.get("type") == "enrichment"]

    assert len(enrichment_events) == 1
    payload = _data(enrichment_events[0])
    assert payload["phase"] == "memory_retrieved"
    assert payload["message"] == "Retrieved 5 memory hits"
    assert payload["scope_type"] == "agent"
    assert payload["scope_id"] == "orchestrator_agent"
    assert payload["scope_name"] == "orchestrator_agent"
    assert payload["memory"] == {
        "mode": "retrieve",
        "hit_count": 5,
        "latency_ms": 125,
    }
