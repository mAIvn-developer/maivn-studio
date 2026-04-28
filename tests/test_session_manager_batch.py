from __future__ import annotations

from types import ModuleType
from typing import Any, cast

import pytest
from langchain_core.messages import HumanMessage, SystemMessage
from maivn import Agent
from maivn_shared import SessionResponse as SharedSessionResponse

import maivn_studio.services.event_bridge as event_bridge_module
from maivn_studio.config.models import DemoConfig
from maivn_studio.services.demo_loader.models import LoadedDemo
from maivn_studio.services.session_manager.manager import SessionManager
from maivn_studio.services.session_manager.models import SessionStatus, StudioSession


class _BatchExecutor:
    name = "batch-executor"

    def __init__(self) -> None:
        self.last_inputs: list[list[Any]] = []
        self.last_kwargs: dict[str, Any] = {}
        self.last_max_concurrency: int | None = None

    def list_tools(self) -> list[Any]:
        return []

    async def abatch(
        self,
        inputs: list[list[Any]],
        *,
        max_concurrency: int | None = None,
        **kwargs: Any,
    ) -> list[SharedSessionResponse]:
        self.last_inputs = inputs
        self.last_kwargs = dict(kwargs)
        self.last_max_concurrency = max_concurrency
        return [
            SharedSessionResponse(responses=[f"done: {messages[-1].content}"])
            for messages in inputs
        ]


class _MatrixExecutor:
    name = "matrix-executor"

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def list_tools(self) -> list[Any]:
        return []

    def invoke(
        self,
        messages: list[Any],
        *,
        thread_id: str | None = None,
        model: str | None = None,
        reasoning: str | None = None,
        targeted_tools: list[str] | None = None,
        **kwargs: Any,
    ) -> SharedSessionResponse:
        self.calls.append(
            {
                "messages": messages,
                "thread_id": thread_id,
                "model": model,
                "reasoning": reasoning,
                "targeted_tools": targeted_tools,
                "kwargs": kwargs,
            }
        )
        return SharedSessionResponse(responses=[f"matrix: {messages[-1].content}"])


def _build_demo_config() -> DemoConfig:
    return DemoConfig(
        id="batch-demo",
        name="Batch Demo",
        module="demos.batch",
    )


@pytest.mark.asyncio
async def test_execute_session_emits_grouped_batch_events() -> None:
    executor = _BatchExecutor()
    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("batch_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )
    session = StudioSession(
        session_id="session-batch",
        demo_config=_build_demo_config(),
        thread_id="thread-batch",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="1. alpha\n2. beta")],
        metadata={
            "batch_config": {
                "messages": ["alpha", "beta"],
                "max_concurrency": 2,
                "async_mode": True,
                "message_type": "human",
            }
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    assert executor.last_max_concurrency == 2
    assert executor.last_kwargs["thread_id"] == "thread-batch"
    assert [messages[-1].content for messages in executor.last_inputs] == ["alpha", "beta"]

    history = bridge.get_history()
    event_types = [event["type"] for event in history]
    assert "batch_start" in event_types
    assert event_types.count("batch_item_complete") == 2
    assert "batch_complete" in event_types
    assert event_types[-1] == "turn_complete"

    batch_complete = next(event for event in history if event["type"] == "batch_complete")
    assert batch_complete["data"]["status"] == "completed"
    assert batch_complete["data"]["item_count"] == 2
    assert [item["response"] for item in batch_complete["data"]["items"]] == [
        "done: alpha",
        "done: beta",
    ]

    turn_complete = history[-1]
    assert turn_complete["data"]["responses"] == []
    assert turn_complete["data"]["batch"]["batch_id"] == batch_complete["data"]["batch_id"]


@pytest.mark.asyncio
async def test_execute_session_batch_matrix_applies_row_overrides() -> None:
    executor = _MatrixExecutor()
    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("batch_matrix_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )
    session = StudioSession(
        session_id="session-matrix",
        demo_config=_build_demo_config(),
        thread_id="thread-matrix",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="1. alpha\n2. beta")],
        metadata={
            "batch_config": {
                "messages": ["alpha", "beta"],
                "rows": [
                    {
                        "label": "Fast API",
                        "message": "alpha",
                        "model": "fast",
                        "reasoning": "low",
                        "targeted_tools": ["lookup"],
                        "system_message": "Use terse output.",
                    },
                    {
                        "label": "Max Billing",
                        "message": "beta",
                        "model": "max",
                        "reasoning": "high",
                    },
                ],
                "max_concurrency": 2,
                "async_mode": True,
                "message_type": "human",
            }
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager._execute_session(session)

    assert [call["model"] for call in executor.calls] == ["fast", "max"]
    assert [call["reasoning"] for call in executor.calls] == ["low", "high"]
    assert executor.calls[0]["targeted_tools"] == ["lookup"]
    assert executor.calls[0]["thread_id"] == "thread-matrix"
    assert any(isinstance(message, SystemMessage) for message in executor.calls[0]["messages"])

    batch_complete = next(
        event for event in bridge.get_history() if event["type"] == "batch_complete"
    )
    assert [item["label"] for item in batch_complete["data"]["items"]] == [
        "Fast API",
        "Max Billing",
    ]
    assert [item["model"] for item in batch_complete["data"]["items"]] == ["fast", "max"]
    assert [item["response"] for item in batch_complete["data"]["items"]] == [
        "matrix: alpha",
        "matrix: beta",
    ]
