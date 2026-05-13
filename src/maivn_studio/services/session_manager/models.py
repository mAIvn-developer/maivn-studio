"""Data models and helpers for session management."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from langchain_core.messages import BaseMessage

from maivn_studio.config.models import AppConfig

from ..app_loader.models import LoadedApp

# MARK: Constants

STUDIO_EVENT_CATEGORIES: tuple[str, ...] = (
    "enrichment",
    "response",
    "func",
    "model",
    "mcp",
    "agent",
    "system",
    "assignment",
    "lifecycle",
)


# MARK: Helpers


def latest_response_text(value: Any) -> str | None:
    """Return the last non-empty string from a list of response texts.

    Used to extract the most recent assistant response from the SDK result's
    ``responses`` list, which may contain multiple synthesized progress texts.
    """
    if not isinstance(value, list):
        return None
    for item in reversed(value):
        if isinstance(item, str) and item.strip():
            return item.strip()
    return None


# MARK: Queued Message


@dataclass
class QueuedMessage:
    """A message staged for delivery on the next turn boundary.

    When a user sends a follow-up while the session is still RUNNING,
    the message is enqueued and automatically consumed once the current
    turn completes.
    """

    content: str
    message_type: str = "human"
    attachments: list[dict[str, Any]] | None = None
    structured_output: dict[str, Any] | None = None
    invocation_kwargs: dict[str, Any] | None = None
    batch_config: dict[str, Any] | None = None


# MARK: Session Status


class SessionStatus(str, Enum):
    """Session execution status.

    Lifecycle for multi-turn conversations:
    CREATED -> RUNNING -> READY (awaiting next message)
                      -> WAITING_INPUT (awaiting interrupt response)
                      -> FAILED
                      -> CANCELLED

    READY state allows follow-up messages for multi-turn chat.
    """

    CREATED = "created"
    RUNNING = "running"
    READY = "ready"  # Completed a turn, ready for follow-up messages
    WAITING_INPUT = "waiting_input"  # Awaiting interrupt response
    COMPLETED = "completed"  # Explicitly ended by user
    FAILED = "failed"
    CANCELLED = "cancelled"


# MARK: Session Model


@dataclass
class StudioSession:
    """Represents an active app execution session."""

    session_id: str
    app_config: AppConfig
    thread_id: str
    variant: str | None = None
    status: SessionStatus = SessionStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    messages: list[BaseMessage] = field(default_factory=list)
    result: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    queued_messages: list[QueuedMessage] = field(default_factory=list, repr=False)

    # Internal state
    _loaded_app: LoadedApp | None = field(default=None, repr=False)
    _task: asyncio.Task | None = field(default=None, repr=False)

    @property
    def can_send_message(self) -> bool:
        """Check if session can receive a new message."""
        return self.status == SessionStatus.READY

    @property
    def can_stage_message(self) -> bool:
        """Check if session can accept a queued message for the next turn."""
        return self.status == SessionStatus.RUNNING

    @property
    def queued_message_count(self) -> int:
        """Number of messages waiting to be consumed on the next turn boundary."""
        return len(self.queued_messages)

    @property
    def is_active(self) -> bool:
        """Check if session is still active (not terminal)."""
        return self.status not in (
            SessionStatus.COMPLETED,
            SessionStatus.FAILED,
            SessionStatus.CANCELLED,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert session to dictionary for API response."""
        return {
            "session_id": self.session_id,
            "app_id": self.app_config.id,
            "app_name": self.app_config.name,
            "thread_id": self.thread_id,
            "variant": self.variant,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "message_count": len(self.messages),
            "can_send_message": self.can_send_message,
            "can_stage_message": self.can_stage_message,
            "queued_message_count": self.queued_message_count,
            "is_active": self.is_active,
            "error": self.error,
        }
