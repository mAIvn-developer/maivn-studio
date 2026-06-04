# pyright: strict
"""Tests for session route handlers and helper functions."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute
from maivn_shared import SessionOrchestrationConfig, SystemToolsConfig

from maivn_studio.api.routes.sessions import models as sessions_models
from maivn_studio.api.routes.sessions import reads as sessions_reads
from maivn_studio.api.routes.sessions import routes as sessions_routes
from maivn_studio.api.routes.sessions import writes as sessions_writes
from maivn_studio.api.routes.sessions.helpers import (
    build_batch_config,
    build_invocation_kwargs,
    build_structured_output_config,
)
from maivn_studio.api.routes.sessions.models import (
    BatchInvocationRequest,
    BatchInvocationRowRequest,
    InvocationConfig,
    StructuredOutputRequest,
)

# MARK: Helpers - build_structured_output_config


class TestBuildStructuredOutputConfig:
    def test_returns_none_when_none(self) -> None:
        assert build_structured_output_config(None) is None

    def test_returns_none_when_disabled(self) -> None:
        req = StructuredOutputRequest(enabled=False)
        assert build_structured_output_config(req) is None

    def test_returns_config_when_enabled(self) -> None:
        req = StructuredOutputRequest(
            enabled=True,
            tool_name="my_tool",
            schema_name="MySchema",
            json_schema={"type": "object"},
        )
        result = build_structured_output_config(req)
        assert result == {
            "tool_name": "my_tool",
            "schema_name": "MySchema",
            "schema": {"type": "object"},
        }

    def test_returns_config_with_nones(self) -> None:
        req = StructuredOutputRequest(enabled=True)
        result = build_structured_output_config(req)
        assert result == {
            "tool_name": None,
            "schema_name": None,
            "schema": None,
        }


# MARK: Helpers - build_invocation_kwargs


class TestBuildInvocationKwargs:
    def test_returns_empty_when_none(self) -> None:
        assert build_invocation_kwargs(None) == {}

    def test_returns_empty_for_defaults(self) -> None:
        config = InvocationConfig()
        result = build_invocation_kwargs(config)
        assert result == {}

    def test_includes_model(self) -> None:
        config = InvocationConfig(model="fast")
        result = build_invocation_kwargs(config)
        assert result["model"] == "fast"

    def test_includes_reasoning(self) -> None:
        config = InvocationConfig(reasoning="high")
        result = build_invocation_kwargs(config)
        assert result["reasoning"] == "high"

    def test_includes_force_final_tool(self) -> None:
        config = InvocationConfig(force_final_tool=True)
        result = build_invocation_kwargs(config)
        assert result["force_final_tool"] is True

    def test_excludes_force_final_tool_when_false(self) -> None:
        config = InvocationConfig(force_final_tool=False)
        result = build_invocation_kwargs(config)
        assert "force_final_tool" not in result

    def test_includes_stream_response_false(self) -> None:
        config = InvocationConfig(stream_response=False)
        result = build_invocation_kwargs(config)
        assert result["stream_response"] is False

    def test_excludes_stream_response_true(self) -> None:
        config = InvocationConfig(stream_response=True)
        result = build_invocation_kwargs(config)
        assert "stream_response" not in result

    def test_includes_status_messages(self) -> None:
        config = InvocationConfig(status_messages=True)
        result = build_invocation_kwargs(config)
        assert result["status_messages"] is True

    def test_excludes_status_messages_false(self) -> None:
        config = InvocationConfig(status_messages=False)
        result = build_invocation_kwargs(config)
        assert "status_messages" not in result

    def test_includes_targeted_tools(self) -> None:
        config = InvocationConfig(targeted_tools=["tool_a", "tool_b"])
        result = build_invocation_kwargs(config)
        assert result["targeted_tools"] == ["tool_a", "tool_b"]

    def test_includes_metadata(self) -> None:
        config = InvocationConfig(metadata={"key": "value"})
        result = build_invocation_kwargs(config)
        assert result["metadata"] == {"key": "value"}

    def test_includes_typed_session_configs(self) -> None:
        config = InvocationConfig(
            system_tools_config=SystemToolsConfig(allowed_tools=["web_search"]),
            orchestration_config=SessionOrchestrationConfig(max_cycles=2),
        )
        result = build_invocation_kwargs(config)
        assert result["system_tools_config"].allowed_tools == ["web_search"]
        assert result["orchestration_config"].max_cycles == 2

    def test_includes_allow_private_in_system_tools(self) -> None:
        config = InvocationConfig(allow_private_in_system_tools=True)
        result = build_invocation_kwargs(config)
        assert result["allow_private_in_system_tools"] is True

    def test_full_config(self) -> None:
        config = InvocationConfig(
            model="balanced",
            reasoning="medium",
            force_final_tool=True,
            stream_response=False,
            status_messages=True,
            targeted_tools=["t1"],
            metadata={"m": 1},
            system_tools_config=SystemToolsConfig(allowed_tools=["web_search"]),
            orchestration_config=SessionOrchestrationConfig(max_cycles=2),
            allow_private_in_system_tools=False,
        )
        result = build_invocation_kwargs(config)
        assert result["model"] == "balanced"
        assert result["reasoning"] == "medium"
        assert result["force_final_tool"] is True
        assert result["stream_response"] is False
        assert result["status_messages"] is True
        assert result["targeted_tools"] == ["t1"]
        assert result["metadata"] == {"m": 1}
        assert result["system_tools_config"].allowed_tools == ["web_search"]
        assert result["orchestration_config"].max_cycles == 2
        assert result["allow_private_in_system_tools"] is False


# MARK: Helpers - build_batch_config


class TestBuildBatchConfig:
    def test_returns_none_when_none_or_disabled(self) -> None:
        assert build_batch_config(None, message_type="human", attachments=None) is None
        assert (
            build_batch_config(
                BatchInvocationRequest(enabled=False),
                message_type="human",
                attachments=None,
            )
            is None
        )

    def test_returns_config_when_enabled(self) -> None:
        attachments = [{"name": "sample.txt", "content_base64": "YWJj"}]
        result = build_batch_config(
            BatchInvocationRequest(
                enabled=True,
                messages=["alpha", "beta"],
                max_concurrency=2,
                async_mode=False,
            ),
            message_type="redacted",
            attachments=attachments,
        )
        assert result == {
            "messages": ["alpha", "beta"],
            "rows": [],
            "max_concurrency": 2,
            "async_mode": False,
            "message_type": "redacted",
            "attachments": attachments,
        }

    def test_batch_request_strips_empty_messages(self) -> None:
        request = BatchInvocationRequest(
            enabled=True,
            messages=[" alpha ", "", " beta "],
        )
        assert request.messages == ["alpha", "beta"]

    def test_returns_matrix_rows_when_enabled(self) -> None:
        result = build_batch_config(
            BatchInvocationRequest(
                enabled=True,
                rows=[
                    BatchInvocationRowRequest.model_validate(
                        {
                            "label": " A ",
                            "message": " alpha ",
                            "variant": "agent-sync",
                            "model": "fast",
                            "reasoning": "low",
                            "targeted_tools": [" lookup ", ""],
                            "system_message": " terse ",
                        }
                    )
                ],
            ),
            message_type="human",
            attachments=None,
        )

        assert result == {
            "messages": ["alpha"],
            "rows": [
                {
                    "label": "A",
                    "message": "alpha",
                    "variant": "agent-sync",
                    "model": "fast",
                    "reasoning": "low",
                    "system_message": "terse",
                    "targeted_tools": ["lookup"],
                }
            ],
            "max_concurrency": None,
            "async_mode": True,
            "message_type": "human",
            "attachments": None,
        }


# MARK: Fake Models


class _FakeStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class _FakeSession:
    session_id: str = "sess-1"
    app_id: str = "app-1"
    app_name: str = "App One"
    thread_id: str = "thread-1"
    variant: str | None = None
    status: _FakeStatus = _FakeStatus.READY
    created_at: str = "2025-01-01T00:00:00"
    started_at: str | None = None
    completed_at: str | None = None
    message_count: int = 0
    can_send_message: bool = True
    can_stage_message: bool = False
    queued_message_count: int = 0
    is_active: bool = True
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "app_id": self.app_id,
            "app_name": self.app_name,
            "thread_id": self.thread_id,
            "variant": self.variant,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "message_count": self.message_count,
            "can_send_message": self.can_send_message,
            "can_stage_message": self.can_stage_message,
            "queued_message_count": self.queued_message_count,
            "is_active": self.is_active,
            "error": self.error,
        }


class _FakeSessionManager:
    def __init__(self, sessions: list[_FakeSession] | None = None) -> None:
        self._sessions = sessions or []
        self._by_thread: dict[str, list[_FakeSession]] = {}
        for s in self._sessions:
            self._by_thread.setdefault(s.thread_id, []).append(s)

    @property
    def sessions(self) -> list[_FakeSession]:
        return list(self._sessions)

    def get(self, session_id: str) -> _FakeSession | None:
        for s in self._sessions:
            if s.session_id == session_id:
                return s
        return None

    def get_by_thread(self, thread_id: str) -> list[_FakeSession]:
        return self._by_thread.get(thread_id, [])

    async def send_message(self, session: Any, message: str, **kwargs: Any) -> None:
        pass

    async def submit_interrupt(self, session: Any, data_key: str, value: Any) -> None:
        pass

    async def end_session(self, session: Any) -> None:
        pass

    async def cancel_session(self, session: Any) -> None:
        pass


# MARK: list_sessions


class TestListSessions:
    @pytest.mark.asyncio
    async def test_empty_list(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(sessions_reads, "get_session_manager", lambda: _FakeSessionManager())
        result = await sessions_reads.list_sessions()
        assert result.total == 0
        assert result.sessions == []

    @pytest.mark.asyncio
    async def test_with_sessions(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s1 = _FakeSession(session_id="s1")
        s2 = _FakeSession(session_id="s2")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s1, s2]),
        )
        result = await sessions_reads.list_sessions()
        assert result.total == 2
        assert len(result.sessions) == 2

    @pytest.mark.asyncio
    async def test_filter_by_status(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s1 = _FakeSession(session_id="s1", status=_FakeStatus.READY)
        s2 = _FakeSession(session_id="s2", status=_FakeStatus.COMPLETED)
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s1, s2]),
        )
        # Use the SessionStatus enum that routes.py actually compares against

        monkeypatch.setattr(sessions_reads, "SessionStatus", _FakeStatus)
        result = await sessions_reads.list_sessions(status="ready")
        assert result.total == 1
        assert result.sessions[0].session_id == "s1"

    @pytest.mark.asyncio
    async def test_filter_by_invalid_status_returns_all(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s1 = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s1]),
        )
        result = await sessions_reads.list_sessions(status="nonexistent")
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_filter_by_thread_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s1 = _FakeSession(session_id="s1", thread_id="t1")
        s2 = _FakeSession(session_id="s2", thread_id="t2")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s1, s2]),
        )
        result = await sessions_reads.list_sessions(thread_id="t1")
        assert result.total == 1
        assert result.sessions[0].session_id == "s1"

    @pytest.mark.asyncio
    async def test_filter_by_thread_id_no_match(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s1 = _FakeSession(session_id="s1", thread_id="t1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s1]),
        )
        result = await sessions_reads.list_sessions(thread_id="t-missing")
        assert result.total == 0


# MARK: get_session


class TestGetSession:
    @pytest.mark.asyncio
    async def test_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        result = await sessions_reads.get_session("s1")
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_reads.get_session("missing")
        assert exc_info.value.status_code == 404


# MARK: get_session_events


class TestGetSessionEvents:
    @pytest.mark.asyncio
    async def test_returns_sse_response(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        mock_bridge = MagicMock()
        mock_bridge.generate_sse = MagicMock(return_value=iter([]))

        def _get_bridge(_session_id: str) -> MagicMock:
            return mock_bridge

        monkeypatch.setattr(sessions_reads, "get_event_bridge", _get_bridge)

        from sse_starlette.sse import EventSourceResponse

        result = await sessions_reads.get_session_events("s1")
        assert isinstance(result, EventSourceResponse)

    @pytest.mark.asyncio
    async def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_reads.get_session_events("missing")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_creates_bridge_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )

        def _no_bridge(_session_id: str) -> MagicMock | None:
            return None

        monkeypatch.setattr(sessions_reads, "get_event_bridge", _no_bridge)
        mock_bridge = MagicMock()
        mock_bridge.generate_sse = MagicMock(return_value=iter([]))

        def _create_bridge(_session_id: str) -> MagicMock:
            return mock_bridge

        monkeypatch.setattr(sessions_reads, "create_event_bridge", _create_bridge)

        result = await sessions_reads.get_session_events("s1")
        from sse_starlette.sse import EventSourceResponse

        assert isinstance(result, EventSourceResponse)


class TestSendMessage:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1", can_send_message=True)
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        request = sessions_models.SendMessageRequest(message="hello")
        result = await sessions_writes.send_message("s1", request)
        assert result.session_id == "s1"
        assert s.metadata["_wait_for_event_subscriber"] is True

    @pytest.mark.asyncio
    async def test_session_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        request = sessions_models.SendMessageRequest(message="hello")
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.send_message("missing", request)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_session_not_ready(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(
            session_id="s1",
            can_send_message=False,
            can_stage_message=False,
            status=_FakeStatus.COMPLETED,
        )
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        request = sessions_models.SendMessageRequest(message="hello")
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.send_message("s1", request)
        assert exc_info.value.status_code == 400


# MARK: submit_interrupt


class TestSubmitInterrupt:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )

        def _resolve(_id: str, _val: str) -> bool:
            return True

        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.interrupts.resolve_interrupt",
            _resolve,
        )
        request = sessions_models.SubmitInterruptRequest(
            interrupt_id="int-1",
            data_key="name",
            value="Alice",
        )
        result = await sessions_writes.submit_interrupt("s1", request)
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_session_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        request = sessions_models.SubmitInterruptRequest(
            data_key="name",
            value="Alice",
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.submit_interrupt("missing", request)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_uses_data_key_when_no_interrupt_id(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _FakeSession(session_id="s1")
        resolved_ids: list[str] = []

        def _capture_resolve(interrupt_id: str, _value: str) -> bool:
            resolved_ids.append(interrupt_id)
            return True

        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.interrupts.resolve_interrupt",
            _capture_resolve,
        )
        request = sessions_models.SubmitInterruptRequest(
            interrupt_id=None,
            data_key="the_key",
            value="val",
        )
        await sessions_writes.submit_interrupt("s1", request)
        assert resolved_ids == ["s1:the_key"]

    @pytest.mark.asyncio
    async def test_falls_back_to_session_scoped_data_key_when_interrupt_id_misses(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        s = _FakeSession(session_id="s1")
        resolved_ids: list[str] = []

        def _capture_resolve(interrupt_id: str, _value: str) -> bool:
            resolved_ids.append(interrupt_id)
            return interrupt_id == "s1:user_name"

        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        monkeypatch.setattr(
            "maivn_studio.services.studio_reporter.interrupts.resolve_interrupt",
            _capture_resolve,
        )
        request = sessions_models.SubmitInterruptRequest(
            interrupt_id="replay-interrupt-id",
            data_key="user_name",
            value="Chad",
        )

        await sessions_writes.submit_interrupt("s1", request)

        assert resolved_ids == ["replay-interrupt-id", "s1:user_name"]


# MARK: end_session


class TestEndSession:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        result = await sessions_writes.end_session("s1")
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.end_session("missing")
        assert exc_info.value.status_code == 404


# MARK: cancel_session


class TestCancelSession:
    @pytest.mark.asyncio
    async def test_delete_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        result = await sessions_writes.cancel_session("s1")
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_delete_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.cancel_session("missing")
        assert exc_info.value.status_code == 404


# MARK: cancel_session_compat


class TestCancelSessionCompat:
    @pytest.mark.asyncio
    async def test_compat_endpoint(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        result = await sessions_writes.cancel_session_compat("s1")
        assert result.session_id == "s1"

    @pytest.mark.asyncio
    async def test_compat_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_writes,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_writes.cancel_session_compat("missing")
        assert exc_info.value.status_code == 404


# MARK: get_session_history


class TestGetSessionHistory:
    @pytest.mark.asyncio
    async def test_with_bridge(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )
        mock_bridge = MagicMock()
        mock_bridge.get_history.return_value = [
            {"type": "enrichment", "data": {"phase": "planning"}},
        ]

        def _get_bridge(_session_id: str) -> MagicMock:
            return mock_bridge

        monkeypatch.setattr(sessions_reads, "get_event_bridge", _get_bridge)

        result = await sessions_reads.get_session_history("s1")
        assert result["session_id"] == "s1"
        assert result["total"] == 1
        assert len(cast(Sequence[object], result["events"])) == 1

    @pytest.mark.asyncio
    async def test_without_bridge(self, monkeypatch: pytest.MonkeyPatch) -> None:
        s = _FakeSession(session_id="s1")
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager([s]),
        )

        def _no_bridge(_session_id: str) -> MagicMock | None:
            return None

        monkeypatch.setattr(sessions_reads, "get_event_bridge", _no_bridge)

        result = await sessions_reads.get_session_history("s1")
        assert result["session_id"] == "s1"
        assert result["total"] == 0
        assert result["events"] == []

    @pytest.mark.asyncio
    async def test_not_found(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(
            sessions_reads,
            "get_session_manager",
            lambda: _FakeSessionManager(),
        )
        with pytest.raises(HTTPException) as exc_info:
            await sessions_reads.get_session_history("missing")
        assert exc_info.value.status_code == 404


# MARK: Router Registration


class TestSessionRouterRegistration:
    def test_root_routes_use_distinct_trailing_slash_aliases(self) -> None:
        registered_routes = {
            (route.path, tuple(sorted(route.methods)))
            for route in sessions_routes.router.routes
            if isinstance(route, APIRoute)
        }

        assert ("/api/sessions", ("GET",)) in registered_routes
        assert ("/api/sessions/", ("GET",)) in registered_routes
        assert ("/api/sessions", ("POST",)) in registered_routes
        assert ("/api/sessions/", ("POST",)) in registered_routes

    def test_router_does_not_register_identical_path_method_pairs(self) -> None:
        registered_routes = [
            (route.path, tuple(sorted(route.methods)))
            for route in sessions_routes.router.routes
            if isinstance(route, APIRoute)
        ]

        assert len(registered_routes) == len(set(registered_routes))
