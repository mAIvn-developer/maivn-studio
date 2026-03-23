"""Tests for session manager models."""

from __future__ import annotations

from datetime import datetime

from langchain_core.messages import HumanMessage

from maivn_studio.config.models import DemoConfig
from maivn_studio.services.session_manager.models import (
    QueuedMessage,
    SessionStatus,
    StudioSession,
    _latest_response_text,
)

# MARK: SessionStatus


class TestSessionStatus:
    def test_all_values(self) -> None:
        assert SessionStatus.CREATED.value == "created"
        assert SessionStatus.RUNNING.value == "running"
        assert SessionStatus.READY.value == "ready"
        assert SessionStatus.WAITING_INPUT.value == "waiting_input"
        assert SessionStatus.COMPLETED.value == "completed"
        assert SessionStatus.FAILED.value == "failed"
        assert SessionStatus.CANCELLED.value == "cancelled"

    def test_is_string_enum(self) -> None:
        assert isinstance(SessionStatus.CREATED, str)
        assert SessionStatus.RUNNING == "running"


# MARK: can_send_message


class TestCanSendMessage:
    def _session(self, status: SessionStatus) -> StudioSession:
        return StudioSession(
            session_id="test",
            demo_config=DemoConfig(id="d1", name="Demo", module="m"),
            thread_id="t1",
            status=status,
        )

    def test_ready_can_send(self) -> None:
        assert self._session(SessionStatus.READY).can_send_message is True

    def test_running_cannot_send(self) -> None:
        assert self._session(SessionStatus.RUNNING).can_send_message is False

    def test_created_cannot_send(self) -> None:
        assert self._session(SessionStatus.CREATED).can_send_message is False

    def test_completed_cannot_send(self) -> None:
        assert self._session(SessionStatus.COMPLETED).can_send_message is False

    def test_failed_cannot_send(self) -> None:
        assert self._session(SessionStatus.FAILED).can_send_message is False

    def test_waiting_input_cannot_send(self) -> None:
        assert self._session(SessionStatus.WAITING_INPUT).can_send_message is False


# MARK: can_stage_message


class TestCanStageMessage:
    def _session(self, status: SessionStatus) -> StudioSession:
        return StudioSession(
            session_id="test",
            demo_config=DemoConfig(id="d1", name="Demo", module="m"),
            thread_id="t1",
            status=status,
        )

    def test_running_can_stage(self) -> None:
        assert self._session(SessionStatus.RUNNING).can_stage_message is True

    def test_ready_cannot_stage(self) -> None:
        assert self._session(SessionStatus.READY).can_stage_message is False

    def test_created_cannot_stage(self) -> None:
        assert self._session(SessionStatus.CREATED).can_stage_message is False

    def test_completed_cannot_stage(self) -> None:
        assert self._session(SessionStatus.COMPLETED).can_stage_message is False


# MARK: is_active


class TestIsActive:
    def _session(self, status: SessionStatus) -> StudioSession:
        return StudioSession(
            session_id="test",
            demo_config=DemoConfig(id="d1", name="Demo", module="m"),
            thread_id="t1",
            status=status,
        )

    def test_active_statuses(self) -> None:
        for status in (
            SessionStatus.CREATED,
            SessionStatus.RUNNING,
            SessionStatus.READY,
            SessionStatus.WAITING_INPUT,
        ):
            assert self._session(status).is_active is True, f"{status} should be active"

    def test_terminal_statuses(self) -> None:
        for status in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        ):
            assert self._session(status).is_active is False, f"{status} should be terminal"


# MARK: queued_message_count


class TestQueuedMessageCount:
    def test_empty_queue(self) -> None:
        session = StudioSession(
            session_id="test",
            demo_config=DemoConfig(id="d1", name="Demo", module="m"),
            thread_id="t1",
        )
        assert session.queued_message_count == 0

    def test_with_messages(self) -> None:
        session = StudioSession(
            session_id="test",
            demo_config=DemoConfig(id="d1", name="Demo", module="m"),
            thread_id="t1",
            queued_messages=[
                QueuedMessage(content="msg1"),
                QueuedMessage(content="msg2"),
                QueuedMessage(content="msg3"),
            ],
        )
        assert session.queued_message_count == 3


# MARK: to_dict


class TestToDict:
    def test_full_dict(self) -> None:
        now = datetime(2025, 1, 15, 12, 0, 0)
        started = datetime(2025, 1, 15, 12, 0, 1)
        completed = datetime(2025, 1, 15, 12, 0, 5)

        session = StudioSession(
            session_id="sess-123",
            demo_config=DemoConfig(id="d1", name="Demo One", module="m.one"),
            thread_id="thread-abc",
            variant="fast",
            status=SessionStatus.COMPLETED,
            created_at=now,
            started_at=started,
            completed_at=completed,
            messages=[HumanMessage(content="hello")],
            error=None,
            queued_messages=[QueuedMessage(content="queued")],
        )

        d = session.to_dict()
        assert d["session_id"] == "sess-123"
        assert d["demo_id"] == "d1"
        assert d["demo_name"] == "Demo One"
        assert d["thread_id"] == "thread-abc"
        assert d["variant"] == "fast"
        assert d["status"] == "completed"
        assert d["created_at"] == now.isoformat()
        assert d["started_at"] == started.isoformat()
        assert d["completed_at"] == completed.isoformat()
        assert d["message_count"] == 1
        assert d["can_send_message"] is False
        assert d["can_stage_message"] is False
        assert d["queued_message_count"] == 1
        assert d["is_active"] is False
        assert d["error"] is None

    def test_dict_with_none_timestamps(self) -> None:
        session = StudioSession(
            session_id="s1",
            demo_config=DemoConfig(id="d1", name="D", module="m"),
            thread_id="t1",
            status=SessionStatus.CREATED,
        )
        d = session.to_dict()
        assert d["started_at"] is None
        assert d["completed_at"] is None

    def test_dict_with_error(self) -> None:
        session = StudioSession(
            session_id="s1",
            demo_config=DemoConfig(id="d1", name="D", module="m"),
            thread_id="t1",
            status=SessionStatus.FAILED,
            error="Something went wrong",
        )
        d = session.to_dict()
        assert d["error"] == "Something went wrong"
        assert d["is_active"] is False


# MARK: _latest_response_text


class TestLatestResponseText:
    def test_returns_last_non_empty(self) -> None:
        assert _latest_response_text(["first", "second", "third"]) == "third"

    def test_skips_empty_strings(self) -> None:
        assert _latest_response_text(["hello", "", "  "]) == "hello"

    def test_strips_whitespace(self) -> None:
        assert _latest_response_text(["  trimmed  "]) == "trimmed"

    def test_not_a_list(self) -> None:
        assert _latest_response_text("not a list") is None
        assert _latest_response_text(None) is None
        assert _latest_response_text(42) is None

    def test_empty_list(self) -> None:
        assert _latest_response_text([]) is None

    def test_all_empty(self) -> None:
        assert _latest_response_text(["", "  ", ""]) is None

    def test_non_string_items(self) -> None:
        assert _latest_response_text([123, None, "actual"]) == "actual"
