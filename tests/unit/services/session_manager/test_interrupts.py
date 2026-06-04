# pyright: strict
from __future__ import annotations

import pytest

from maivn_studio.config.models import AppConfig
from maivn_studio.services.session_manager.lifecycle import submit_interrupt_response
from maivn_studio.services.session_manager.models import SessionStatus, StudioSession


def _build_session(*, status: SessionStatus) -> StudioSession:
    return StudioSession(
        session_id="session-1",
        app_config=AppConfig(id="app-1", name="App", module="app.module"),
        thread_id="thread-1",
        status=status,
    )


@pytest.mark.asyncio
async def test_submit_interrupt_response_accepts_ready_session() -> None:
    session = _build_session(status=SessionStatus.READY)

    await submit_interrupt_response(
        session,
        data_key="user_name",
        value="Chad",
    )

    assert session.status == SessionStatus.RUNNING
    assert session.metadata["interrupt_responses"]["user_name"] == "Chad"


@pytest.mark.asyncio
async def test_submit_interrupt_response_rejects_terminal_session() -> None:
    session = _build_session(status=SessionStatus.COMPLETED)

    with pytest.raises(ValueError, match="not accepting interrupts"):
        await submit_interrupt_response(
            session,
            data_key="user_name",
            value="Chad",
        )
