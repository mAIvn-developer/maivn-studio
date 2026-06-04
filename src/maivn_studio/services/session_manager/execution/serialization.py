"""Serialization helpers for structured output and token usage."""

# pyright: strict
from __future__ import annotations

from typing import SupportsInt, cast

from pydantic import BaseModel

# MARK: Token Usage Keys

_TOKEN_USAGE_KEYS: tuple[str, ...] = (
    "total_tokens",
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_creation_tokens",
    "reasoning_tokens",
)


# MARK: Structured Output


def serialize_structured_result(result: object) -> object | None:
    """Convert a Pydantic structured result into a JSON-safe dict, or pass through."""
    if result is None:
        return None
    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


# MARK: Token Usage


def serialize_token_usage(token_usage: object) -> dict[str, int] | None:
    """Normalize a token-usage object into a plain dict for SSE payloads."""
    if token_usage is None:
        return None

    return {key: _read_int_attr(token_usage, key) for key in _TOKEN_USAGE_KEYS}


def sum_token_usage(items: list[dict[str, object]]) -> dict[str, int] | None:
    """Sum per-item token usage dicts into a single aggregate for batch turns."""
    token_items: list[dict[str, object]] = [
        usage for item in items if isinstance((usage := item.get("token_usage")), dict) and usage
    ]
    if not token_items:
        return None

    return {
        key: sum(int(cast(SupportsInt, usage.get(key, 0))) for usage in token_items)
        for key in _TOKEN_USAGE_KEYS
    }


# MARK: Helpers


def _read_int_attr(source: object, name: str) -> int:
    value = getattr(source, name, 0)
    if isinstance(value, int):
        return value
    return int(cast(SupportsInt, value))


__all__ = [
    "serialize_structured_result",
    "serialize_token_usage",
    "sum_token_usage",
]
