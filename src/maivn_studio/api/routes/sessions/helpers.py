from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from maivn_studio.config.loader import get_config_path, reload_config, set_config
from maivn_studio.discovery.registry import init_registry
from maivn_studio.services.session_manager.manager import get_session_manager

from .models import (
    BatchInvocationRequest,
    InvocationConfig,
    MessageAttachmentPayload,
    StructuredOutputRequest,
)

logger = logging.getLogger(__name__)


# MARK: Registry


def refresh_registry_from_disk() -> None:
    try:
        config_path = get_config_path()
        config = reload_config()
        set_config(config, config_path)
        base_path = config_path.parent if config_path is not None else Path.cwd()
        init_registry(config, base_path)
    except Exception as exc:
        logger.warning("Failed to refresh studio registry from disk before session start: %s", exc)


# MARK: Session Helpers


def get_session_or_404(session_id: str, *, manager: Any | None = None) -> Any:
    active_manager = manager or get_session_manager()
    session = active_manager.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")
    return session


# MARK: Request Helpers


def build_structured_output_config(
    structured_output: StructuredOutputRequest | None,
) -> dict[str, Any] | None:
    if structured_output and structured_output.enabled:
        return {
            "tool_name": structured_output.tool_name,
            "schema_name": structured_output.schema_name,
            "schema": structured_output.json_schema,
        }
    return None


def build_invocation_kwargs(invocation: InvocationConfig | None) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if invocation is None:
        return kwargs

    if invocation.model is not None:
        kwargs["model"] = invocation.model
    if invocation.reasoning is not None:
        kwargs["reasoning"] = invocation.reasoning
    if invocation.force_final_tool:
        kwargs["force_final_tool"] = True
    if invocation.stream_response is not True:
        kwargs["stream_response"] = invocation.stream_response
    if invocation.status_messages:
        kwargs["status_messages"] = True
    if invocation.targeted_tools is not None:
        kwargs["targeted_tools"] = invocation.targeted_tools
    if invocation.metadata is not None:
        kwargs["metadata"] = invocation.metadata
    if invocation.memory_config is not None:
        kwargs["memory_config"] = invocation.memory_config
    if invocation.system_tools_config is not None:
        kwargs["system_tools_config"] = invocation.system_tools_config
    if invocation.orchestration_config is not None:
        kwargs["orchestration_config"] = invocation.orchestration_config
    if invocation.allow_private_in_system_tools is not None:
        kwargs["allow_private_in_system_tools"] = invocation.allow_private_in_system_tools

    return kwargs


def build_batch_config(
    batch: BatchInvocationRequest | None,
    *,
    message_type: str,
    attachments: list[dict[str, Any]] | None,
) -> dict[str, Any] | None:
    if batch is None or not batch.enabled:
        return None

    rows = [row.model_dump(exclude_none=True) for row in batch.rows]
    messages = list(batch.messages)
    if rows and not messages:
        messages = [str(row["message"]) for row in rows]

    return {
        "messages": messages,
        "rows": rows,
        "max_concurrency": batch.max_concurrency,
        "async_mode": batch.async_mode,
        "message_type": message_type,
        "attachments": attachments,
    }


def serialize_attachments(
    attachments: list[MessageAttachmentPayload] | None,
) -> list[dict[str, Any]] | None:
    if not attachments:
        return None
    return [item.model_dump(exclude_none=True) for item in attachments]


def merge_private_data(
    *private_data_sources: dict[str, Any] | None,
) -> dict[str, Any] | None:
    merged_private_data: dict[str, Any] = {}
    for source in private_data_sources:
        if source:
            merged_private_data.update(source)

    log_path_value = merged_private_data.get("log_path")
    if isinstance(log_path_value, str) and (
        log_path_value in ("", ".", "./")
        or not Path(log_path_value).is_absolute()
        or (Path(log_path_value).exists() and not Path(log_path_value).is_file())
    ):
        merged_private_data.pop("log_path", None)

    return merged_private_data or None
