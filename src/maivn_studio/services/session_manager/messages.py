"""Message helpers for session management."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

try:
    from maivn.messages import HumanMessage as SDKHumanMessage
    from maivn.messages import RedactedMessage
except ImportError:
    SDKHumanMessage = HumanMessage
    RedactedMessage = None  # type: ignore[assignment, misc]

from .models import QueuedMessage, StudioSession

# MARK: Turn Configuration


def apply_turn_configuration(
    session: StudioSession,
    *,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
    batch_config: dict[str, Any] | None = None,
) -> None:
    """Set or clear per-turn structured output and invocation kwargs in session metadata."""
    if structured_output:
        session.metadata["structured_output"] = structured_output
    else:
        session.metadata.pop("structured_output", None)

    if invocation_kwargs:
        session.metadata["invocation_kwargs"] = invocation_kwargs
    else:
        session.metadata.pop("invocation_kwargs", None)

    if batch_config:
        session.metadata["batch_config"] = batch_config
    else:
        session.metadata.pop("batch_config", None)


def resolve_structured_output_metadata_fallback(
    *,
    loaded_demo: Any,
    structured_output_model: type[Any] | None,
    user_invoke_kwargs: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Reuse demo-level metadata when structured output turns omit it."""
    if structured_output_model is None:
        return None
    if isinstance(user_invoke_kwargs, dict) and "metadata" in user_invoke_kwargs:
        metadata = user_invoke_kwargs.get("metadata")
        return dict(metadata) if isinstance(metadata, dict) else None

    default_invocation = getattr(loaded_demo, "default_invocation", None)
    if not isinstance(default_invocation, dict):
        return None

    default_metadata = default_invocation.get("metadata")
    if not isinstance(default_metadata, dict):
        return None

    return dict(default_metadata)


# MARK: Message Queue


def enqueue_message(
    session: StudioSession,
    *,
    message: str,
    message_type: str,
    attachments: list[dict[str, Any]] | None,
    structured_output: dict[str, Any] | None,
    invocation_kwargs: dict[str, Any] | None,
    batch_config: dict[str, Any] | None,
) -> None:
    """Append a message to the session's queue for deferred delivery."""
    session.queued_messages.append(
        QueuedMessage(
            content=message,
            message_type=message_type,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
        )
    )


def consume_queued_messages(
    session: StudioSession,
    *,
    create_message_fn: Callable[..., BaseMessage],
) -> tuple[int, dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
    """Drain queued messages into the session message history."""
    queued_messages = list(session.queued_messages)
    if not queued_messages:
        return 0, None, None, None

    session.queued_messages.clear()
    next_structured_output: dict[str, Any] | None = None
    next_invocation_kwargs: dict[str, Any] | None = None
    next_batch_config: dict[str, Any] | None = None

    for queued in queued_messages:
        session.messages.append(
            create_message_fn(
                queued.content,
                queued.message_type,
                attachments=queued.attachments,
            )
        )
        next_structured_output = queued.structured_output
        next_invocation_kwargs = queued.invocation_kwargs
        next_batch_config = queued.batch_config

    return len(queued_messages), next_structured_output, next_invocation_kwargs, next_batch_config


# MARK: Message Construction


def create_message(
    content: str,
    message_type: str,
    *,
    attachments: list[dict[str, Any]] | None = None,
) -> BaseMessage:
    """Create a message of the appropriate type."""
    if message_type == "redacted" and RedactedMessage is not None:
        return RedactedMessage(content=content, attachments=attachments)
    if message_type == "system":
        return SystemMessage(content=content)
    return SDKHumanMessage(content=content, attachments=attachments)
