"""Serialization helpers for structured output and token usage."""

from __future__ import annotations

from typing import Any

# MARK: Structured Output


def serialize_structured_result(result: Any) -> Any:
    """Convert a Pydantic structured result into a JSON-safe dict, or pass through."""
    if result is None:
        return None

    from pydantic import BaseModel

    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


# MARK: Token Usage


def serialize_token_usage(token_usage: Any) -> dict[str, int] | None:
    """Normalize a token-usage object into a plain dict for SSE payloads."""
    if token_usage is None:
        return None

    return {
        "total_tokens": getattr(token_usage, "total_tokens", 0),
        "input_tokens": getattr(token_usage, "input_tokens", 0),
        "output_tokens": getattr(token_usage, "output_tokens", 0),
        "cache_read_tokens": getattr(token_usage, "cache_read_tokens", 0),
        "cache_creation_tokens": getattr(token_usage, "cache_creation_tokens", 0),
        "reasoning_tokens": getattr(token_usage, "reasoning_tokens", 0),
    }


def sum_token_usage(items: list[dict[str, Any]]) -> dict[str, int] | None:
    """Sum per-item token usage dicts into a single aggregate for batch turns."""
    token_items = [item.get("token_usage") for item in items if item.get("token_usage")]
    if not token_items:
        return None

    keys = (
        "total_tokens",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "cache_creation_tokens",
        "reasoning_tokens",
    )
    return {
        key: sum(
            int(token_usage.get(key, 0))
            for token_usage in token_items
            if isinstance(token_usage, dict)
        )
        for key in keys
    }


__all__ = [
    "serialize_structured_result",
    "serialize_token_usage",
    "sum_token_usage",
]
