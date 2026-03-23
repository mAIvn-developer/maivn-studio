from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import ModuleType
from typing import Any, cast

import maivn._internal.core.entities as core_entities
import pytest
from langchain_core.messages import HumanMessage
from maivn import Agent
from maivn._internal.utils.reporting.context import current_reporter, current_sdk_delivery_mode
from maivn_shared import (
    FINAL_EVENT_NAME,
    INTERRUPT_REQUIRED_EVENT_NAME,
    STATUS_MESSAGE_EVENT_NAME,
    TOOL_EVENT_NAME,
    UPDATE_EVENT_NAME,
    create_uuid,
)
from maivn_shared import SessionResponse as SharedSessionResponse
from pydantic import BaseModel

import maivn_studio.services.event_bridge as event_bridge_module
import maivn_studio.services.session_manager.execution as session_execution_module
import maivn_studio.services.session_manager.lifecycle as session_manager_lifecycle_module
from maivn_studio.config.models import DemoConfig
from maivn_studio.services.demo_loader.models import LoadedDemo
from maivn_studio.services.session_manager.manager import SessionManager
from maivn_studio.services.session_manager.models import SessionStatus, StudioSession


class _StructuredPayload(BaseModel):
    answer: str


class _DummyModelTool:
    def __init__(self, name: str, model: type[BaseModel]) -> None:
        self.name = name
        self.model = model


class _DummySessionResult:
    def __init__(self) -> None:
        self.response = "done"
        self.result = {"ok": True}
        self.token_usage = None
        self.responses = ["done"]


class _DummyStreamEvent:
    def __init__(self, *, name: str, payload: dict[str, Any]) -> None:
        self.name = name
        self.payload = payload


class _DummyEventInvocable:
    def __init__(
        self,
        *,
        stream_events: list[_DummyStreamEvent] | None = None,
        on_stream: Callable[[], None] | None = None,
    ) -> None:
        self.last_invoke_kwargs: dict[str, Any] = {}
        self.last_stream_kwargs: dict[str, Any] = {}
        self.last_invoke_delivery_mode: str | None = None
        self.last_stream_delivery_mode: str | None = None
        self._stream_events = stream_events
        self._on_stream = on_stream

    def invoke(self, **kwargs: Any) -> _DummySessionResult:
        self.last_invoke_kwargs = dict(kwargs)
        self.last_invoke_delivery_mode = current_sdk_delivery_mode.get()
        return _DummySessionResult()

    def stream(self, **kwargs: Any) -> list[_DummyStreamEvent]:
        self.last_stream_kwargs = dict(kwargs)
        self.last_stream_delivery_mode = current_sdk_delivery_mode.get()
        if self._on_stream is not None:
            self._on_stream()
        if self._stream_events is not None:
            return list(self._stream_events)
        final_payload = SharedSessionResponse(responses=["streamed done"]).model_dump()
        return [_DummyStreamEvent(name=FINAL_EVENT_NAME, payload=final_payload)]


class _DummyExecutor:
    name = "dummy-executor"

    def __init__(
        self,
        model_tool: _DummyModelTool,
        *,
        event_invocable: _DummyEventInvocable | None = None,
    ) -> None:
        self._model_tool = model_tool
        self.event_invocable = event_invocable or _DummyEventInvocable()

    def list_tools(self) -> list[_DummyModelTool]:
        return [self._model_tool]

    def events(self, **_: Any) -> _DummyEventInvocable:
        return self.event_invocable

    def stream(self, **kwargs: Any) -> list[_DummyStreamEvent]:
        return self.event_invocable.stream(**kwargs)

    def invoke(self, **_: Any) -> _DummySessionResult:
        return _DummySessionResult()


class _DummyLegacyStructuredInvocable:
    def __init__(self) -> None:
        self.last_invoke_kwargs: dict[str, Any] = {}

    def invoke(self, **kwargs: Any) -> _DummySessionResult:
        self.last_invoke_kwargs = dict(kwargs)
        return _DummySessionResult()


class _DummyLegacyExecutor:
    name = "dummy-legacy-executor"

    def __init__(self, model_tool: _DummyModelTool) -> None:
        self._model_tool = model_tool
        self.event_invocable = _DummyEventInvocable()
        self.structured_invocable = _DummyLegacyStructuredInvocable()

    def list_tools(self) -> list[_DummyModelTool]:
        return [self._model_tool]

    def events(self, **_: Any) -> _DummyEventInvocable:
        return self.event_invocable

    def structured_output(self, _model: type[BaseModel]) -> _DummyLegacyStructuredInvocable:
        return self.structured_invocable

    def invoke(self, messages: list[Any]) -> _DummySessionResult:
        _ = messages
        return _DummySessionResult()


def _build_demo_config() -> DemoConfig:
    return DemoConfig(
        id="demo-id",
        name="Demo",
        module="demos.example",
    )


class _DummyBackgroundTask:
    def done(self) -> bool:
        return True


class _ShutdownTask:
    def __init__(self) -> None:
        self.cancelled = False

    def done(self) -> bool:
        return False

    def cancel(self) -> None:
        self.cancelled = True

    def __await__(self):
        if False:
            yield
        raise asyncio.CancelledError


class _CloseableExecutor:
    name = "closeable-executor"

    def __init__(self) -> None:
        self.close_calls = 0

    def close(self) -> None:
        self.close_calls += 1


class _DummyAgentTool:
    def __init__(self) -> None:
        self.tool_id = "agent-tool-1"
        self.name = "Data Analyzer"
        self.tool_type = "agent"
        self.target_agent_id = "agent-2"


class _DummySwarmAgent:
    def __init__(self, *, agent_id: str, name: str) -> None:
        self.id = agent_id
        self.name = name


class _DummySwarm:
    def __init__(self) -> None:
        self.name = "Research Swarm"
        self.agents = [_DummySwarmAgent(agent_id="agent-final", name="Research Coordinator")]

    def list_tools(self) -> list[Any]:
        return []


class _ExecutorWithSwarmLookup:
    def __init__(self) -> None:
        self.name = "executor-with-swarm"
        self._swarm = _DummySwarm()

    def list_tools(self) -> list[Any]:
        return []

    def get_swarm(self) -> _DummySwarm:
        return self._swarm


class _StreamingContractExecutor:
    name = "streaming-contract-executor"

    def __init__(
        self,
        *,
        stream_events: list[_DummyStreamEvent],
        on_stream: Callable[[], None] | None = None,
    ) -> None:
        self._tool = _DummyAgentTool()
        self.event_invocable = _DummyEventInvocable(
            stream_events=stream_events,
            on_stream=on_stream,
        )

    def list_tools(self) -> list[_DummyAgentTool]:
        return [self._tool]

    def events(self, **_: Any) -> _DummyEventInvocable:
        return self.event_invocable

    def stream(self, **kwargs: Any) -> list[_DummyStreamEvent]:
        return self.event_invocable.stream(**kwargs)

    def invoke(self, **_: Any) -> _DummySessionResult:
        return _DummySessionResult()


class _OrderingEventInvocable:
    def invoke(self, **kwargs: Any) -> _DummySessionResult:
        _ = kwargs
        reporter = cast(Any, current_reporter.get())
        assert reporter is not None

        reporter.report_tool_start(
            tool_name="Research Coordinator",
            event_id="primary-agent-tool",
            tool_type="agent",
            agent_name="Research Coordinator",
            swarm_name="Research Swarm",
            tool_args={"agent_id": "agent-primary"},
        )
        reporter.report_agent_assignment(
            agent_name="Data Analyzer",
            status="in_progress",
            assignment_id="nested-agent-assignment",
            swarm_name="Research Swarm",
        )
        reporter.report_tool_start(
            tool_name="fetch_data",
            event_id="fetch-data-tool",
            tool_type="func",
            agent_name="Research Coordinator",
            swarm_name="Research Swarm",
            tool_args={"source": "customer_behavior"},
        )
        return _DummySessionResult()


class _OrderingExecutor:
    name = "ordering-executor"

    def __init__(self) -> None:
        self.event_invocable = _OrderingEventInvocable()

    def list_tools(self) -> list[Any]:
        return []

    def events(self, **_: Any) -> _OrderingEventInvocable:
        return self.event_invocable

    def invoke(self, **_: Any) -> _DummySessionResult:
        return _DummySessionResult()


@pytest.mark.asyncio
async def test_execute_session_ignores_targeted_tools_with_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("test_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-structured-output",
        demo_config=_build_demo_config(),
        thread_id="thread-1",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "structured_output": {"tool_name": "schema_tool"},
            "invocation_kwargs": {
                "targeted_tools": ["alpha_tool"],
                "model": "balanced",
            },
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "_emit_event", _emit_event_noop)

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    invoke_kwargs = executor.event_invocable.last_invoke_kwargs
    assert invoke_kwargs.get("structured_output") is _StructuredPayload
    assert "targeted_tools" not in invoke_kwargs
    assert invoke_kwargs.get("model") == "balanced"


@pytest.mark.asyncio
async def test_execute_session_uses_default_invocation_metadata_for_structured_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("test_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
        default_invocation={
            "force_final_tool": True,
            "metadata": {"allowed_system_tools": []},
        },
    )

    session = StudioSession(
        session_id="session-structured-output-default-metadata",
        demo_config=_build_demo_config(),
        thread_id="thread-default-metadata",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "structured_output": {"tool_name": "schema_tool"},
            "invocation_kwargs": {
                "force_final_tool": True,
            },
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "_emit_event", _emit_event_noop)

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    invoke_kwargs = executor.event_invocable.last_invoke_kwargs
    assert invoke_kwargs.get("structured_output") is _StructuredPayload
    assert invoke_kwargs.get("metadata") == {"allowed_system_tools": []}
    assert invoke_kwargs.get("force_final_tool") is True


@pytest.mark.asyncio
async def test_execute_session_preserves_metadata_on_legacy_structured_output_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyLegacyExecutor(model_tool=model_tool)

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("test_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-legacy-structured-output",
        demo_config=_build_demo_config(),
        thread_id="thread-legacy",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "structured_output": {"tool_name": "schema_tool"},
            "invocation_kwargs": {
                "force_final_tool": True,
                "targeted_tools": ["alpha_tool"],
                "metadata": {"allowed_system_tools": []},
                "allow_private_in_system_tools": True,
            },
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "_emit_event", _emit_event_noop)

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    invoke_kwargs = executor.structured_invocable.last_invoke_kwargs
    assert invoke_kwargs.get("force_final_tool") is True
    assert invoke_kwargs.get("metadata") == {"allowed_system_tools": []}
    assert invoke_kwargs.get("allow_private_in_system_tools") is True
    assert "targeted_tools" not in invoke_kwargs


@pytest.mark.asyncio
async def test_execute_session_uses_stream_path_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("test_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-stream-default",
        demo_config=_build_demo_config(),
        thread_id="thread-stream-default",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "invocation_kwargs": {
                "model": "balanced",
            },
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "_emit_event", _emit_event_noop)

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    assert executor.event_invocable.last_stream_kwargs.get("model") == "balanced"
    assert executor.event_invocable.last_stream_delivery_mode == "stream"
    assert executor.event_invocable.last_invoke_kwargs == {}


@pytest.mark.asyncio
async def test_execute_session_forwards_normalized_contract_stream_events_to_bridge() -> None:
    final_payload = SharedSessionResponse(responses=["streamed done"]).model_dump()

    def _report_runtime_tool_start() -> None:
        reporter = cast(Any, current_reporter.get())
        assert reporter is not None
        reporter.report_tool_start(
            tool_name="Data Analyzer",
            event_id="agent-tool-1",
            tool_type="agent",
            agent_name="Data Analyzer",
            tool_args={"agent_id": "agent-2", "prompt": "Analyze the dataset"},
        )

    executor = _StreamingContractExecutor(
        stream_events=[
            _DummyStreamEvent(
                name=UPDATE_EVENT_NAME,
                payload={"assistant_id": "assistant-2", "streaming_content": "Analyzing now"},
            ),
            _DummyStreamEvent(
                name=INTERRUPT_REQUIRED_EVENT_NAME,
                payload={
                    "interrupt_id": "int-1",
                    "checkpoint_id": "cp-1",
                    "data_key": "email",
                    "prompt": "Enter email",
                    "tool_name": "Data Analyzer",
                    "input_type": "text",
                    "choices": [],
                },
            ),
            _DummyStreamEvent(name=FINAL_EVENT_NAME, payload=final_payload),
        ],
        on_stream=_report_runtime_tool_start,
    )

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("stream_contract_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-contract-stream",
        demo_config=_build_demo_config(),
        thread_id="thread-contract-stream",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager._execute_session(session)
    await asyncio.sleep(0.05)

    history = bridge.get_history()
    tool_events = [event for event in history if event.get("type") == "tool_event"]
    assistant_chunks = [event for event in history if event.get("type") == "assistant_chunk"]
    interrupts = [event for event in history if event.get("type") == "interrupt_required"]

    assert any(event["data"]["tool_type"] == "agent" for event in tool_events)
    assert any(event["data"]["tool_name"] == "Data Analyzer" for event in tool_events)
    assert any(event["data"]["args"].get("agent_id") == "agent-2" for event in tool_events)
    assert [event["data"]["text"] for event in assistant_chunks] == ["Analyzing now"]
    assert len(interrupts) == 1
    assert interrupts[0]["data"]["interrupt_id"] == "int-1"
    assert interrupts[0]["data"]["data_key"] == "email"
    assert executor.event_invocable.last_stream_delivery_mode == "stream"


@pytest.mark.asyncio
async def test_execute_session_replay_ownership_skips_normalized_tool_and_status_events() -> None:
    final_payload = SharedSessionResponse(responses=["streamed done"]).model_dump()

    def _emit_reporter_owned_events() -> None:
        reporter = cast(Any, current_reporter.get())
        assert reporter is not None

        reporter.report_tool_start(
            tool_name="fetch_data",
            event_id="reporter-tool-start-1",
            tool_type="func",
            agent_name="Research Coordinator",
            tool_args={"source": "customer_behavior"},
        )
        reporter.report_status_message(
            "Reporter-owned status",
            assistant_id="orchestrator_agent",
        )

    executor = _StreamingContractExecutor(
        stream_events=[
            _DummyStreamEvent(
                name=TOOL_EVENT_NAME,
                payload={
                    "value": {
                        "tool_call": {
                            "id": "normalized-tool-start-2",
                            "name": "fetch_data",
                            "type": "func",
                            "args": {"source": "customer_behavior"},
                        }
                    }
                },
            ),
            _DummyStreamEvent(
                name=STATUS_MESSAGE_EVENT_NAME,
                payload={
                    "assistant_id": "orchestrator_agent",
                    "message": "Normalized status should not replay",
                },
            ),
            _DummyStreamEvent(name=FINAL_EVENT_NAME, payload=final_payload),
        ],
        on_stream=_emit_reporter_owned_events,
    )

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("stream_contract_ownership_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-contract-ownership",
        demo_config=_build_demo_config(),
        thread_id="thread-contract-ownership",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager._execute_session(session)
    await asyncio.sleep(0.05)

    history = bridge.get_history()
    tool_events = [event for event in history if event.get("type") == "tool_event"]
    status_events = [event for event in history if event.get("type") == "status_message"]

    assert len(tool_events) == 1
    assert tool_events[0]["data"]["tool_id"] == "reporter-tool-start-1"
    assert tool_events[0]["data"]["tool_name"] == "fetch_data"
    assert tool_events[0]["data"]["status"] == "executing"
    assert len(status_events) == 1
    assert status_events[0]["data"]["assistant_id"] == "orchestrator_agent"
    assert status_events[0]["data"]["message"] == "Reporter-owned status"


def test_studio_contract_stream_replay_ownership_is_explicit() -> None:
    assert session_execution_module._should_replay_event_to_reporter("assistant_chunk") is True
    assert session_execution_module._should_replay_event_to_reporter("system_tool_chunk") is True
    assert session_execution_module._should_replay_event_to_reporter("status_message") is False
    assert session_execution_module._should_replay_event_to_reporter("tool_event") is False
    assert session_execution_module._should_replay_event_to_bridge("interrupt_required") is True
    assert session_execution_module._should_replay_event_to_bridge("status_message") is False


@pytest.mark.asyncio
async def test_execute_session_emits_turn_complete_after_pending_reporter_events() -> None:
    executor = _OrderingExecutor()
    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("ordering_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-ordering",
        demo_config=_build_demo_config(),
        thread_id="thread-ordering",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={"invocation_kwargs": {"stream_response": False}},
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    original_emit = bridge.emit

    async def delayed_emit(event_type: str, data: dict[str, Any]) -> None:
        if event_type in {"tool_event", "agent_assignment"}:
            await asyncio.sleep(0.02)
        await original_emit(event_type, data)

    bridge.emit = delayed_emit  # type: ignore[method-assign]

    await manager._execute_session(session)

    initial_types = [event["type"] for event in bridge.get_history()]
    assert initial_types[-1] == "turn_complete"
    assert "tool_event" in initial_types[:-1]
    assert "agent_assignment" in initial_types[:-1]

    await asyncio.sleep(0.05)

    settled_types = [event["type"] for event in bridge.get_history()]
    assert settled_types[-1] == "turn_complete"
    assert settled_types.count("tool_event") >= 2
    assert settled_types.count("agent_assignment") == 1


def test_build_tool_contract_maps_includes_swarm_invocation_tool_ids() -> None:
    executor = _ExecutorWithSwarmLookup()

    tool_name_map, tool_metadata_map = cast(Any, SessionManager)._build_tool_contract_maps(executor)

    invocation_tool_id = create_uuid("agent_invoke_agent-final")
    assert tool_name_map[invocation_tool_id] == "Research Coordinator"
    assert tool_metadata_map[invocation_tool_id]["tool_name"] == "Research Coordinator"
    assert tool_metadata_map[invocation_tool_id]["tool_type"] == "agent"
    assert tool_metadata_map[invocation_tool_id]["target_agent_id"] == "agent-final"
    assert tool_metadata_map[invocation_tool_id]["agent_name"] == "Research Coordinator"
    assert tool_metadata_map[invocation_tool_id]["swarm_name"] == "Research Swarm"


@pytest.mark.asyncio
async def test_execute_session_uses_invoke_path_when_streaming_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("test_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-invoke-explicit",
        demo_config=_build_demo_config(),
        thread_id="thread-invoke-explicit",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "invocation_kwargs": {
                "stream_response": False,
                "model": "fast",
            },
        },
        _loaded_demo=loaded_demo,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "_emit_event", _emit_event_noop)

    await manager._execute_session(session)

    assert session.status == SessionStatus.READY
    assert executor.event_invocable.last_invoke_kwargs.get("stream_response") is False
    assert executor.event_invocable.last_invoke_kwargs.get("model") == "fast"
    assert executor.event_invocable.last_invoke_delivery_mode == "invoke"
    assert executor.event_invocable.last_stream_kwargs == {}


@pytest.mark.asyncio
async def test_start_session_force_reloads_demo_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("reloaded_demo_module"),
        agents=[cast(Agent, object())],
        swarms=[],
    )
    manager = SessionManager()
    session = StudioSession(
        session_id="session-force-reload",
        demo_config=_build_demo_config(),
        thread_id="thread-force-reload",
    )
    captured: dict[str, Any] = {}

    class _LoaderStub:
        def load(
            self,
            config: DemoConfig,
            force_reload: bool = False,
            variant: str | None = None,
        ) -> LoadedDemo:
            captured["config"] = config
            captured["force_reload"] = force_reload
            captured["variant"] = variant
            return loaded_demo

    def _create_task_stub(coro: Any, *, name: str | None = None) -> _DummyBackgroundTask:
        captured["task_name"] = name
        coro.close()
        return _DummyBackgroundTask()

    monkeypatch.setattr(
        session_manager_lifecycle_module,
        "get_demo_loader",
        lambda: _LoaderStub(),
    )
    monkeypatch.setattr(
        session_manager_lifecycle_module.asyncio,
        "create_task",
        _create_task_stub,
    )

    await manager.start_session(session, "reload the demo please")

    assert captured["config"].id == session.demo_config.id
    assert captured["force_reload"] is True
    assert captured["variant"] is None
    assert captured["task_name"] == "session-session-force-reload"
    assert session._loaded_demo is loaded_demo
    assert session.status == SessionStatus.RUNNING


@pytest.mark.asyncio
async def test_shutdown_releases_loaded_demo_resources_and_bridges() -> None:
    executor = _CloseableExecutor()
    loaded_demo = LoadedDemo(
        config=_build_demo_config(),
        module=ModuleType("shutdown_demo_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )
    manager = SessionManager()
    session = StudioSession(
        session_id="session-shutdown",
        demo_config=_build_demo_config(),
        thread_id="thread-shutdown",
        status=SessionStatus.RUNNING,
        _loaded_demo=loaded_demo,
        _task=cast(Any, _ShutdownTask()),
    )
    manager._sessions[session.session_id] = session
    manager._by_thread[session.thread_id] = [session.session_id]

    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager.shutdown()

    assert executor.close_calls == 1
    assert session._loaded_demo is None
    assert session._task is None
    assert manager.sessions == []
    assert event_bridge_module.get_event_bridge(session.session_id) is None
