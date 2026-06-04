# pyright: strict
from __future__ import annotations

import asyncio
from collections.abc import Callable
from types import ModuleType
from typing import Any, cast

import maivn._internal.core.entities as core_entities
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from maivn import Agent
from maivn._internal.utils.reporting.context import (
    current_reporter,
    current_sdk_delivery_mode,
)
from maivn.events import (
    AppEvent,
    NormalizedEventForwardingState,
    build_assistant_chunk_payload,
    build_system_tool_chunk_payload,
)
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
from maivn_studio.config.models import AppConfig
from maivn_studio.services.app_loader.models import LoadedApp
from maivn_studio.services.event_bridge import EventBridge
from maivn_studio.services.session_manager.manager import SessionManager
from maivn_studio.services.session_manager.models import SessionStatus, StudioSession
from maivn_studio.services.studio_reporter.reporter import StudioReporter


def _history(bridge: EventBridge) -> list[dict[str, Any]]:
    """Return the bridge history with entry values narrowed for indexing.

    ``EventBridge.get_history`` returns ``list[dict[str, object]]``; tests
    index into the event payloads, so narrow each entry at the boundary.
    """
    return cast("list[dict[str, Any]]", bridge.get_history())


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


def _build_app_config() -> AppConfig:
    return AppConfig(
        id="app-id",
        name="App",
        module="apps.example",
    )


class _DummyBackgroundTask:
    def done(self) -> bool:
        return True


class _SubscriberWaitBridge:
    def __init__(self, result: bool = True) -> None:
        self.result = result
        self.timeout: float | None = None

    async def wait_for_subscriber(self, timeout: float | None = None) -> bool:
        self.timeout = timeout
        return self.result


class _DummyLogger:
    def __init__(self) -> None:
        self.debug_messages: list[tuple[object, ...]] = []

    def debug(self, msg: object, *args: object) -> None:
        self.debug_messages.append((msg, *args))

    def info(self, msg: object, *args: object) -> None:
        _ = (msg, args)

    def warning(self, msg: object, *args: object) -> None:
        _ = (msg, args)

    def exception(self, msg: object, *args: object) -> None:
        _ = (msg, args)


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

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-structured-output",
        app_config=_build_app_config(),
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
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

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

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
        default_invocation={
            "force_final_tool": True,
            "system_tools_config": {"allowed_tools": []},
        },
    )

    session = StudioSession(
        session_id="session-structured-output-default-metadata",
        app_config=_build_app_config(),
        thread_id="thread-default-metadata",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "structured_output": {"tool_name": "schema_tool"},
            "invocation_kwargs": {
                "force_final_tool": True,
            },
        },
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

    assert session.status == SessionStatus.READY
    invoke_kwargs = executor.event_invocable.last_invoke_kwargs
    assert invoke_kwargs.get("structured_output") is _StructuredPayload
    assert invoke_kwargs.get("system_tools_config") == {"allowed_tools": []}
    assert invoke_kwargs.get("force_final_tool") is True


@pytest.mark.asyncio
async def test_execute_session_preserves_metadata_on_legacy_structured_output_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyLegacyExecutor(model_tool=model_tool)

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-legacy-structured-output",
        app_config=_build_app_config(),
        thread_id="thread-legacy",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "structured_output": {"tool_name": "schema_tool"},
            "invocation_kwargs": {
                "force_final_tool": True,
                "targeted_tools": ["alpha_tool"],
                "system_tools_config": {"allowed_tools": []},
                "allow_private_in_system_tools": True,
            },
        },
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

    assert session.status == SessionStatus.READY
    invoke_kwargs = executor.structured_invocable.last_invoke_kwargs
    assert invoke_kwargs.get("force_final_tool") is True
    assert invoke_kwargs.get("system_tools_config") == {"allowed_tools": []}
    assert invoke_kwargs.get("allow_private_in_system_tools") is True
    assert "targeted_tools" not in invoke_kwargs


@pytest.mark.asyncio
async def test_execute_session_uses_stream_path_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-stream-default",
        app_config=_build_app_config(),
        thread_id="thread-stream-default",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "invocation_kwargs": {
                "model": "balanced",
            },
        },
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

    assert session.status == SessionStatus.READY
    assert executor.event_invocable.last_stream_kwargs.get("model") == "balanced"
    assert executor.event_invocable.last_stream_delivery_mode == "stream"
    assert executor.event_invocable.last_invoke_kwargs == {}


@pytest.mark.asyncio
async def test_execute_session_strips_prior_turn_attachments_from_invocation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core_entities, "ModelTool", _DummyModelTool)

    model_tool = _DummyModelTool(name="schema_tool", model=_StructuredPayload)
    executor = _DummyExecutor(model_tool=model_tool)

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )
    prior_attachment = {
        "name": "prior.txt",
        "mime_type": "text/plain",
        "content_base64": "cHJpb3I=",
    }
    current_attachment = {
        "name": "current.txt",
        "mime_type": "text/plain",
        "content_base64": "Y3VycmVudA==",
    }
    prior_message = HumanMessage(
        content="What is in this attachment?",
        additional_kwargs={"attachments": [prior_attachment]},
    )
    current_message = HumanMessage(
        content="Follow up on that.",
        additional_kwargs={"attachments": [current_attachment]},
    )

    session = StudioSession(
        session_id="session-prior-attachment",
        app_config=_build_app_config(),
        thread_id="thread-prior-attachment",
        status=SessionStatus.RUNNING,
        messages=[
            prior_message,
            AIMessage(content="The attachment had prior context."),
            current_message,
        ],
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

    invoke_messages = cast(list[Any], executor.event_invocable.last_stream_kwargs["messages"])
    prior_kwargs = cast(dict[str, Any], prior_message.additional_kwargs)
    assert invoke_messages[0].additional_kwargs.get("attachments") is None
    assert prior_kwargs["attachments"] == [prior_attachment]
    assert invoke_messages[1].content == "The attachment had prior context."
    assert invoke_messages[2].additional_kwargs["attachments"] == [current_attachment]


@pytest.mark.asyncio
async def test_execute_session_forwards_normalized_contract_stream_events_to_bridge() -> None:
    final_payload = SharedSessionResponse(responses=["Analyzing now"]).model_dump()

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
        reporter.print_final_response("Analyzing now")

    executor = _StreamingContractExecutor(
        stream_events=[
            _DummyStreamEvent(
                name=UPDATE_EVENT_NAME,
                payload={"assistant_id": "assistant-2", "streaming_content": "Analyzing"},
            ),
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

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("stream_contract_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-contract-stream",
        app_config=_build_app_config(),
        thread_id="thread-contract-stream",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        loaded_app=loaded_app,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager.run_session(session)
    await asyncio.sleep(0.05)

    history = _history(bridge)
    tool_events = [event for event in history if event.get("type") == "tool_event"]
    assistant_chunks = [event for event in history if event.get("type") == "assistant_chunk"]
    interrupts = [event for event in history if event.get("type") == "interrupt_required"]

    assert any(event["data"]["tool_type"] == "agent" for event in tool_events)
    assert any(event["data"]["tool_name"] == "Data Analyzer" for event in tool_events)
    assert any(event["data"]["args"].get("agent_id") == "agent-2" for event in tool_events)
    assert [event["data"]["text"] for event in assistant_chunks] == ["Analyzing", " now"]
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

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("stream_contract_ownership_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-contract-ownership",
        app_config=_build_app_config(),
        thread_id="thread-contract-ownership",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        loaded_app=loaded_app,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager.run_session(session)
    await asyncio.sleep(0.05)

    history = _history(bridge)
    tool_events = [event for event in history if event.get("type") == "tool_event"]
    status_events = [event for event in history if event.get("type") == "status_message"]

    assert len(tool_events) == 1
    assert tool_events[0]["data"]["tool_id"] == "reporter-tool-start-1"
    assert tool_events[0]["data"]["tool_name"] == "fetch_data"
    assert tool_events[0]["data"]["status"] == "executing"
    assert len(status_events) == 1
    assert status_events[0]["data"]["assistant_id"] == "orchestrator_agent"
    assert status_events[0]["data"]["message"] == "Reporter-owned status"


@pytest.mark.asyncio
async def test_execute_session_waits_for_event_subscriber_before_emitting_stream_events() -> None:
    final_payload = SharedSessionResponse(responses=["streamed done"]).model_dump()
    executor = _StreamingContractExecutor(
        stream_events=[
            _DummyStreamEvent(
                name=UPDATE_EVENT_NAME,
                payload={"assistant_id": "assistant-1", "streaming_content": "streamed"},
            ),
            _DummyStreamEvent(
                name=UPDATE_EVENT_NAME,
                payload={"assistant_id": "assistant-1", "streaming_content": "streamed done"},
            ),
            _DummyStreamEvent(name=FINAL_EVENT_NAME, payload=final_payload),
        ],
    )

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("subscriber_wait_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-subscriber-wait",
        app_config=_build_app_config(),
        thread_id="thread-subscriber-wait",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={"_wait_for_event_subscriber": True},
        loaded_app=loaded_app,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    task = asyncio.create_task(manager.run_session(session))
    await asyncio.sleep(0.05)

    assert bridge.get_history() == []

    generator = bridge.generate_sse(heartbeat_interval=0.01)
    first_event: dict[str, Any] | None = None
    for _ in range(10):
        candidate = await asyncio.wait_for(anext(generator), timeout=1)
        if "event" in candidate:
            first_event = candidate
            break
    await task
    await generator.aclose()

    assert first_event is not None
    assert first_event["event"] == "session_start"
    history = _history(bridge)
    assistant_chunks = [event for event in history if event.get("type") == "assistant_chunk"]
    assert [event["data"]["text"] for event in assistant_chunks] == ["streamed", " done"]
    assert history[-1]["type"] == "turn_complete"


def test_studio_contract_stream_replay_ownership_is_explicit() -> None:
    assert session_execution_module.should_replay_event_to_reporter("assistant_chunk") is True
    assert session_execution_module.should_replay_event_to_reporter("system_tool_chunk") is True
    assert session_execution_module.should_replay_event_to_reporter("status_message") is False
    assert session_execution_module.should_replay_event_to_reporter("tool_event") is False
    assert session_execution_module.should_replay_event_to_bridge("interrupt_required") is True
    assert session_execution_module.should_replay_event_to_bridge("status_message") is False


@pytest.mark.asyncio
async def test_normalized_replay_emits_reporter_chunks_under_stream_context() -> None:
    loop = asyncio.get_running_loop()
    bridge = event_bridge_module.EventBridge("session-replay-stream-context")
    reporter = StudioReporter(bridge=bridge, loop=loop)
    normalized_events = [
        AppEvent.model_validate(
            build_assistant_chunk_payload(assistant_id="assistant-1", text="Hello")
        ),
        AppEvent.model_validate(
            build_system_tool_chunk_payload(tool_id="system-tool-1", text="thinking")
        ),
    ]

    def _replay_from_stream_context() -> None:
        token = current_sdk_delivery_mode.set("stream")
        try:
            session_execution_module.replay_normalized_events(
                normalized_events,
                reporter=reporter,
                bridge=bridge,
                loop=loop,
                forwarding_state=NormalizedEventForwardingState(),
            )
        finally:
            current_sdk_delivery_mode.reset(token)

    await asyncio.to_thread(_replay_from_stream_context)
    await reporter.flush()

    history = _history(bridge)
    assistant_chunks = [event for event in history if event.get("type") == "assistant_chunk"]
    system_chunks = [event for event in history if event.get("type") == "system_tool_chunk"]
    assert [event["data"]["text"] for event in assistant_chunks] == ["Hello"]
    assert [event["data"]["text"] for event in system_chunks] == ["thinking"]


@pytest.mark.asyncio
async def test_wait_for_event_subscriber_waits_only_when_route_requested() -> None:
    session = StudioSession(
        session_id="session-wait-subscriber",
        app_config=_build_app_config(),
        thread_id="thread-wait-subscriber",
        metadata={"_wait_for_event_subscriber": True},
    )
    bridge = _SubscriberWaitBridge()

    await session_execution_module.wait_for_event_subscriber(
        session=session,
        bridge=bridge,
        logger=_DummyLogger(),
    )

    assert bridge.timeout == session_execution_module.FIRST_EVENT_SUBSCRIBER_WAIT_SECONDS
    assert "_wait_for_event_subscriber" not in session.metadata


@pytest.mark.asyncio
async def test_wait_for_event_subscriber_skips_unflagged_sessions() -> None:
    session = StudioSession(
        session_id="session-no-wait-subscriber",
        app_config=_build_app_config(),
        thread_id="thread-no-wait-subscriber",
    )
    bridge = _SubscriberWaitBridge()

    await session_execution_module.wait_for_event_subscriber(
        session=session,
        bridge=bridge,
        logger=_DummyLogger(),
    )

    assert bridge.timeout is None


@pytest.mark.asyncio
async def test_execute_session_emits_turn_complete_after_pending_reporter_events() -> None:
    executor = _OrderingExecutor()
    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("ordering_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-ordering",
        app_config=_build_app_config(),
        thread_id="thread-ordering",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={"invocation_kwargs": {"stream_response": False}},
        loaded_app=loaded_app,
    )

    manager = SessionManager()
    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    original_emit = bridge.emit

    async def delayed_emit(event_type: str, data: dict[str, Any]) -> None:
        if event_type in {"tool_event", "agent_assignment"}:
            await asyncio.sleep(0.02)
        await original_emit(event_type, data)

    bridge.emit = delayed_emit

    await manager.run_session(session)

    initial_types = [event["type"] for event in _history(bridge)]
    assert initial_types[-1] == "turn_complete"
    assert "tool_event" in initial_types[:-1]
    assert "agent_assignment" in initial_types[:-1]

    await asyncio.sleep(0.05)

    settled_types = [event["type"] for event in _history(bridge)]
    assert settled_types[-1] == "turn_complete"
    assert settled_types.count("tool_event") >= 2
    assert settled_types.count("agent_assignment") == 1


def test_build_tool_contract_maps_includes_swarm_invocation_tool_ids() -> None:
    executor = _ExecutorWithSwarmLookup()

    tool_name_map, tool_metadata_map = cast(Any, SessionManager).build_tool_contract_maps(executor)

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

    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )

    session = StudioSession(
        session_id="session-invoke-explicit",
        app_config=_build_app_config(),
        thread_id="thread-invoke-explicit",
        status=SessionStatus.RUNNING,
        messages=[HumanMessage(content="hello")],
        metadata={
            "invocation_kwargs": {
                "stream_response": False,
                "model": "fast",
            },
        },
        loaded_app=loaded_app,
    )

    manager = SessionManager()

    async def _emit_event_noop(*_: Any, **__: Any) -> None:
        return None

    monkeypatch.setattr(manager, "emit_event", _emit_event_noop)

    await manager.run_session(session)

    assert session.status == SessionStatus.READY
    assert executor.event_invocable.last_invoke_kwargs.get("stream_response") is False
    assert executor.event_invocable.last_invoke_kwargs.get("model") == "fast"
    assert executor.event_invocable.last_invoke_delivery_mode == "invoke"
    assert executor.event_invocable.last_stream_kwargs == {}


@pytest.mark.asyncio
async def test_start_session_force_reloads_app_module(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("reloaded_app_module"),
        agents=[cast(Agent, object())],
        swarms=[],
    )
    manager = SessionManager()
    session = StudioSession(
        session_id="session-force-reload",
        app_config=_build_app_config(),
        thread_id="thread-force-reload",
    )
    captured: dict[str, Any] = {}

    class _LoaderStub:
        def load(
            self,
            config: AppConfig,
            force_reload: bool = False,
            variant: str | None = None,
        ) -> LoadedApp:
            captured["config"] = config
            captured["force_reload"] = force_reload
            captured["variant"] = variant
            return loaded_app

    def _create_task_stub(coro: Any, *, name: str | None = None) -> _DummyBackgroundTask:
        captured["task_name"] = name
        coro.close()
        return _DummyBackgroundTask()

    monkeypatch.setattr(
        session_manager_lifecycle_module,
        "get_app_loader",
        lambda: _LoaderStub(),
    )
    monkeypatch.setattr(
        session_manager_lifecycle_module.asyncio,
        "create_task",
        _create_task_stub,
    )

    await manager.start_session(session, "reload the app please")

    assert captured["config"].id == session.app_config.id
    assert captured["force_reload"] is True
    assert captured["variant"] is None
    assert captured["task_name"] == "session-session-force-reload"
    assert session.loaded_app is loaded_app
    assert session.status == SessionStatus.RUNNING


@pytest.mark.asyncio
async def test_shutdown_releases_loaded_app_resources_and_bridges() -> None:
    executor = _CloseableExecutor()
    loaded_app = LoadedApp(
        config=_build_app_config(),
        module=ModuleType("shutdown_app_module"),
        agents=[cast(Agent, executor)],
        swarms=[],
    )
    manager = SessionManager()
    session = StudioSession(
        session_id="session-shutdown",
        app_config=_build_app_config(),
        thread_id="thread-shutdown",
        status=SessionStatus.RUNNING,
        loaded_app=loaded_app,
        task=cast(Any, _ShutdownTask()),
    )
    manager.sessions_by_id[session.session_id] = session
    manager.by_thread[session.thread_id] = [session.session_id]

    bridge = event_bridge_module.create_event_bridge(session.session_id)
    assert bridge is not None

    await manager.shutdown()

    assert executor.close_calls == 1
    assert session.loaded_app is None
    assert session.task is None
    assert manager.sessions == []
    assert event_bridge_module.get_event_bridge(session.session_id) is None
