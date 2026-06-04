"""Serialization helpers for schedule terminal event payloads."""

# pyright: strict

from __future__ import annotations

from typing import cast

from maivn import RunRecord
from pydantic import BaseModel

from maivn_studio.services.session_manager.models import latest_response_text

# MARK: Token usage / structured result


def duration_ms(record: RunRecord) -> int | None:
    """Return ``record``'s fired→finished duration in milliseconds, or ``None``."""
    if record.fired_at is None or record.finished_at is None:
        return None
    return int((record.finished_at - record.fired_at).total_seconds() * 1000)


def serialize_structured_result(result: object) -> object:
    """Pydantic-aware structured-output serialization for schedule terminals."""
    if result is None:
        return None
    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


def serialize_token_usage(token_usage: object) -> dict[str, int] | None:
    """Normalize a token-usage object into a plain dict for SSE payloads."""
    if token_usage is None:
        return None
    return {
        "total_tokens": _int_attr(token_usage, "total_tokens"),
        "input_tokens": _int_attr(token_usage, "input_tokens"),
        "output_tokens": _int_attr(token_usage, "output_tokens"),
        "cache_read_tokens": _int_attr(token_usage, "cache_read_tokens"),
        "cache_creation_tokens": _int_attr(token_usage, "cache_creation_tokens"),
        "reasoning_tokens": _int_attr(token_usage, "reasoning_tokens"),
    }


def _int_attr(source: object, name: str) -> int:
    """Read an integer attribute off a token-usage object, defaulting to 0."""
    value: object = getattr(source, name, 0)
    return value if isinstance(value, int) else 0


# MARK: Stream result coercion


def coerce_stream_result(result: object) -> object:
    """Convert a stream method's list-of-events result into a SessionResponse.

    ``stream`` / ``astream`` runners return ``list(events)``; the last
    contract event carries the same final payload an ``invoke`` would have
    returned. Clients reconnecting after a fire completes need that payload
    in ``turn_complete`` so the UI can render the response without replaying
    every chunk.
    """
    if not isinstance(result, list):
        return result
    from maivn_shared import FINAL_EVENT_NAME
    from maivn_shared import SessionResponse as SDKSessionResponse

    events = cast("list[object]", result)
    final_payload: dict[str, object] | None = None
    for event in events:
        payload = getattr(event, "payload", None)
        if not isinstance(payload, dict):
            continue
        typed_payload = cast("dict[str, object]", payload)
        if getattr(event, "name", "") == FINAL_EVENT_NAME or typed_payload.get("event_name") == (
            "final"
        ):
            final_payload = typed_payload
    if final_payload is None:
        return events
    try:
        return SDKSessionResponse.model_validate(final_payload)
    except Exception:  # noqa: BLE001 - falling back is harmless; chunks have already streamed
        return events


# MARK: Result payload extraction


def extract_result_payload(result: object) -> dict[str, object]:
    """Flatten a SessionResponse-like object into a JSON-safe payload dict."""
    result = coerce_stream_result(result)
    responses: object = getattr(result, "responses", None)
    response_text = latest_response_text(responses)
    if response_text is None:
        raw_response: object = getattr(result, "response", None)
        response_text = raw_response if isinstance(raw_response, str) else ""

    result_payload = serialize_structured_result(getattr(result, "result", None))
    token_usage = serialize_token_usage(getattr(result, "token_usage", None))

    payload: dict[str, object] = {
        "responses": responses if isinstance(responses, list) else [],
        "response": response_text,
        "result": result_payload,
        "token_usage": token_usage,
    }
    return {key: value for key, value in payload.items() if value is not None}


def build_terminal_event_data(
    *,
    session_id: str,
    schedule_fire_id: str,
    status: str,
    duration_ms: int | None,
    error: str | None,
    result: object,
) -> dict[str, object]:
    """Compose the ``turn_complete``/``error`` payload for a fire's terminal event."""
    result_payload = extract_result_payload(result)
    output: dict[str, object] = {
        "response": result_payload.get("response"),
        "result": result_payload.get("result"),
        "token_usage": result_payload.get("token_usage"),
    }
    base: dict[str, object] = {
        "session_id": session_id,
        "schedule_fire_id": schedule_fire_id,
        "status": status,
        "duration_ms": duration_ms,
        "error": error,
    }
    return {
        **base,
        **result_payload,
        "output": {key: value for key, value in output.items() if value is not None},
    }


__all__ = [
    "build_terminal_event_data",
    "coerce_stream_result",
    "duration_ms",
    "extract_result_payload",
    "serialize_structured_result",
    "serialize_token_usage",
]
