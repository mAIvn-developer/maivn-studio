"""Request and response models for session routes."""

from __future__ import annotations

import base64
import binascii
from typing import Any

from maivn_shared import MemoryConfig
from pydantic import BaseModel, field_validator

# MARK: Invocation Models


class StructuredOutputRequest(BaseModel):
    """Structured output configuration."""

    enabled: bool = False
    tool_name: str | None = None  # Tool to use as schema
    schema_name: str | None = None  # Custom schema name
    json_schema: dict[str, Any] | None = None  # Custom JSON schema


class InvocationConfig(BaseModel):
    """SDK invocation parameters passed through to Agent/Swarm invoke()/stream()."""

    model: str | None = None  # fast, balanced, max
    reasoning: str | None = None  # minimal, low, medium, high
    force_final_tool: bool = False
    stream_response: bool = True
    status_messages: bool = False
    targeted_tools: list[str] | None = None
    metadata: dict[str, Any] | None = None
    memory_config: MemoryConfig | None = None
    allow_private_in_system_tools: bool | None = None


# MARK: Attachment Models


class MessageAttachmentPayload(BaseModel):
    """Attachment payload forwarded to SDK message objects."""

    name: str | None = None
    mime_type: str | None = None
    content_base64: str
    source_url: str | None = None
    sharing_scope: str | None = None
    binding_type: str | None = None
    source_type: str | None = None
    description: str | None = None
    tags: list[str] | None = None

    @field_validator("content_base64")
    @classmethod
    def _validate_content_base64(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("content_base64 is required for attachments")
        try:
            decoded = base64.b64decode(normalized, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("content_base64 must be valid base64") from exc
        if not decoded:
            raise ValueError("content_base64 must decode to non-empty bytes")
        return normalized


# MARK: Request Models


class CreateSessionRequest(BaseModel):
    """Request to create a new session."""

    demo_id: str
    variant: str | None = None
    thread_id: str | None = None
    message: str
    message_type: str = "human"  # human, redacted
    system_message: str | None = None
    attachments: list[MessageAttachmentPayload] | None = None
    private_data: dict[str, Any] | None = None
    structured_output: StructuredOutputRequest | None = None
    invocation: InvocationConfig | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message to a session."""

    message: str
    message_type: str = "human"  # human, redacted, system
    attachments: list[MessageAttachmentPayload] | None = None
    structured_output: StructuredOutputRequest | None = None
    invocation: InvocationConfig | None = None


class SubmitInterruptRequest(BaseModel):
    """Request to submit an interrupt response."""

    interrupt_id: str | None = None
    data_key: str
    value: Any


# MARK: Response Models


class SessionResponse(BaseModel):
    """Response for session operations."""

    session_id: str
    demo_id: str
    demo_name: str
    thread_id: str
    variant: str | None
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None
    message_count: int
    can_send_message: bool
    can_stage_message: bool
    queued_message_count: int
    is_active: bool
    error: str | None


class SessionListResponse(BaseModel):
    """Response for listing sessions."""

    sessions: list[SessionResponse]
    total: int
