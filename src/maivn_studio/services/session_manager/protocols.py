# pyright: strict
"""Shared type contracts for session management.

These protocols and aliases type the ``manager`` and ``executor`` seams
threaded through the extracted lifecycle / event / execution helpers, so
each helper module agrees on one structural contract instead of falling
back to ``Any``.
"""

from __future__ import annotations

from collections.abc import Coroutine
from typing import Any, Protocol

from langchain_core.messages import BaseMessage

from ..app_loader.models import Executor
from .models import StudioSession

__all__ = ["Executor", "SessionManagerLike"]


# MARK: Session Manager Protocol


class SessionManagerLike(Protocol):
    """Callback seam the lifecycle/event helpers invoke on the manager.

    Declares only the members the extracted helpers reach back into, so the
    free functions can stay decoupled from the concrete ``SessionManager``
    while remaining fully typed.
    """

    async def emit_event(
        self,
        session: StudioSession,
        event_type: str,
        data: dict[str, Any],
    ) -> None: ...

    def create_message(
        self,
        content: str,
        message_type: str,
        *,
        attachments: list[dict[str, Any]] | None = None,
    ) -> BaseMessage: ...

    def enqueue_message(
        self,
        session: StudioSession,
        *,
        message: str,
        message_type: str,
        attachments: list[dict[str, Any]] | None,
        structured_output: dict[str, Any] | None,
        invocation_kwargs: dict[str, Any] | None,
        batch_config: dict[str, Any] | None,
    ) -> None: ...

    def run_session(self, session: StudioSession) -> Coroutine[Any, Any, None]: ...
