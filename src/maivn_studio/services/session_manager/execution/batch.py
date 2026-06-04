"""Batch invocation execution for Studio sessions.

Implements the batch turn loop that fans out per-row invocations across the
SDK's ``batch`` / ``abatch`` paths or a per-row matrix runner for rows that
need their own variant + private data context.

The matrix runner exists because the SDK's bulk batch APIs assume one shared
executor; rows with their own ``variant`` need a freshly reloaded app, which
means each row gets its own executor instance.
"""

# pyright: strict
from __future__ import annotations

import asyncio
import contextvars
import inspect
import time
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast

from langchain_core.messages import BaseMessage, HumanMessage
from pydantic import BaseModel

from ...app_loader.models import Executor, LoadedApp
from ..messages import resolve_structured_output_invocation_fallbacks
from ..models import StudioSession, latest_response_text
from .capabilities import LoggerLike, supports_structured_output_kwarg
from .protocols import ExecutionManagerLike
from .serialization import (
    serialize_structured_result,
    serialize_token_usage,
    sum_token_usage,
)

# MARK: Batch Result Models


@dataclass
class BatchTurnResult:
    """Aggregated outcome of a single batch turn: per-item responses + the event payload."""

    responses: list[object]
    event_data: dict[str, Any]


@dataclass
class BatchInputSpec:
    """One row of a batch invocation, with optional per-row variant overrides."""

    index: int
    message: str
    messages: list[BaseMessage]
    label: str | None = None
    variant: str | None = None
    invocation: dict[str, Any] | None = None
    system_message: str | None = None

    @property
    def has_row_overrides(self) -> bool:
        return bool(self.variant or self.system_message or self.invocation)


# MARK: Helpers


def _as_object_list(value: object) -> list[object]:
    """Return ``value`` as a ``list[object]`` when it is a list, else an empty list.

    The batch config arrives as ``dict[str, Any]``; narrowing those ``Any`` values
    to ``list`` yields ``list[Unknown]``. Funneling them through this helper gives
    callers a list of the known ``object`` element type so the per-item
    ``isinstance`` filters narrow cleanly.
    """
    if isinstance(value, list):
        return cast("list[object]", value)
    return []


# MARK: Item Serialization


def _serialize_batch_response(
    result: object,
    *,
    spec: BatchInputSpec,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    responses = getattr(result, "responses", None)
    response_text = latest_response_text(responses)
    if response_text is None:
        raw_response = getattr(result, "response", None)
        response_text = raw_response if isinstance(raw_response, str) else ""

    item: dict[str, Any] = {
        "index": spec.index,
        "label": spec.label,
        "input": spec.message,
        "status": "completed",
        "variant": spec.variant,
        "model": spec.invocation.get("model") if spec.invocation else None,
        "reasoning": spec.invocation.get("reasoning") if spec.invocation else None,
        "responses": responses if isinstance(responses, list) else [],
        "response": response_text,
        "result": serialize_structured_result(getattr(result, "result", None)),
        "duration_ms": duration_ms,
        "token_usage": serialize_token_usage(getattr(result, "token_usage", None)),
    }
    return {key: value for key, value in item.items() if value is not None}


def _serialize_batch_pending_spec(spec: BatchInputSpec) -> dict[str, Any]:
    item: dict[str, Any] = {
        "index": spec.index,
        "label": spec.label,
        "input": spec.message,
        "status": "pending",
        "variant": spec.variant,
        "model": spec.invocation.get("model") if spec.invocation else None,
        "reasoning": spec.invocation.get("reasoning") if spec.invocation else None,
    }
    return {key: value for key, value in item.items() if value is not None}


# MARK: Input Building


def _build_batch_inputs(
    manager: ExecutionManagerLike,
    session: StudioSession,
    batch_config: dict[str, Any],
) -> list[BatchInputSpec]:
    raw_messages = _as_object_list(batch_config.get("messages"))
    messages = [item.strip() for item in raw_messages if isinstance(item, str) and item.strip()]

    raw_rows = _as_object_list(batch_config.get("rows"))
    candidate_rows: list[dict[str, Any]] = [
        cast("dict[str, Any]", row) for row in raw_rows if isinstance(row, dict)
    ]
    rows: list[dict[str, Any]] = [
        row for row in candidate_rows if str(row.get("message", "")).strip()
    ]
    if not rows:
        rows = [{"message": message} for message in messages]
    if not rows:
        raise ValueError("Batch execution requires at least one input message")

    base_messages = list(session.messages)
    if base_messages:
        base_messages = base_messages[:-1]

    message_type = batch_config.get("message_type")
    if not isinstance(message_type, str) or not message_type:
        message_type = "human"
    raw_attachments = batch_config.get("attachments")
    attachments: list[dict[str, Any]] | None = (
        cast("list[dict[str, Any]]", raw_attachments) if isinstance(raw_attachments, list) else None
    )

    batch_inputs: list[BatchInputSpec] = []
    for index, row in enumerate(rows):
        message = str(row.get("message", "")).strip()
        row_messages = list(base_messages)
        system_message = row.get("system_message")
        if isinstance(system_message, str) and system_message.strip():
            row_messages.append(manager.create_message(system_message.strip(), "system"))
        row_messages.append(
            manager.create_message(
                message,
                message_type,
                attachments=attachments,
            )
        )

        invocation: dict[str, Any] = {}
        for key in ("model", "reasoning"):
            value = row.get(key)
            if isinstance(value, str) and value.strip():
                invocation[key] = value.strip()
        targeted_tools = row.get("targeted_tools")
        if isinstance(targeted_tools, list):
            tools = [
                item.strip()
                for item in cast("list[object]", targeted_tools)
                if isinstance(item, str) and item.strip()
            ]
            if tools:
                invocation["targeted_tools"] = tools

        label = row.get("label")
        variant = row.get("variant")
        batch_inputs.append(
            BatchInputSpec(
                index=index,
                label=label.strip() if isinstance(label, str) and label.strip() else None,
                message=message,
                messages=row_messages,
                variant=variant.strip() if isinstance(variant, str) and variant.strip() else None,
                invocation=invocation or None,
                system_message=system_message.strip()
                if isinstance(system_message, str) and system_message.strip()
                else None,
            )
        )
    return batch_inputs


# MARK: Structured Output Resolution


def _resolve_structured_output_model(
    *,
    session: StudioSession,
    executor: Executor,
    structured_output_config: object,
    logger: LoggerLike,
) -> type[BaseModel] | None:
    if not isinstance(structured_output_config, dict):
        return None

    tool_name: object = cast("dict[str, Any]", structured_output_config).get("tool_name")
    if not tool_name:
        return None

    from maivn._internal.core.entities import (
        ModelTool,
    )

    model_class: type[BaseModel] | None = None
    for tool in executor.list_tools():
        if tool.name == tool_name:
            if isinstance(tool, ModelTool):
                model_class = tool.model
            break

    if model_class:
        logger.info(
            "Session %s using structured_output with model: %s (from tool: %s)",
            session.session_id,
            model_class.__name__,
            tool_name,
        )
        return model_class

    logger.warning(
        "Session %s: Tool %s not found or is not a ModelTool, ignoring structured_output config",
        session.session_id,
        tool_name,
    )
    session.metadata["structured_output_warning"] = (
        f'Tool "{tool_name}" not found or is not a ModelTool'
    )
    return None


# MARK: Invoke Kwargs Assembly


def _build_base_invoke_kwargs(
    *,
    loaded: LoadedApp,
    session: StudioSession,
    structured_output_model: type[BaseModel] | None,
) -> dict[str, Any]:
    invoke_kwargs: dict[str, Any] = {
        "messages": session.messages,
        "thread_id": session.thread_id,
    }

    user_invoke_kwargs = session.metadata.get("invocation_kwargs")
    fallback_invocation_kwargs = resolve_structured_output_invocation_fallbacks(
        loaded_app=loaded,
        structured_output_model=structured_output_model,
        user_invoke_kwargs=user_invoke_kwargs,
    )
    invoke_kwargs.update(fallback_invocation_kwargs)
    if isinstance(user_invoke_kwargs, dict):
        invoke_kwargs.update(cast("dict[str, Any]", user_invoke_kwargs))

    invoke_kwargs.pop("verbose", None)
    return invoke_kwargs


# MARK: Per-Row Executor Resolution


def _resolve_row_executor(
    *,
    session: StudioSession,
    executor: Executor,
    spec: BatchInputSpec,
    logger: LoggerLike,
) -> Executor:
    if not spec.variant or spec.variant == session.variant:
        return executor

    if spec.variant not in session.app_config.variants:
        raise ValueError(f"Unknown batch row variant: {spec.variant}")

    from maivn_studio.services.app_loader.loader import get_app_loader
    from maivn_studio.services.session_manager.private_data import apply_private_data

    row_loaded = get_app_loader().load(
        session.app_config,
        force_reload=True,
        variant=spec.variant,
    )
    user_private_data = session.metadata.get("user_private_data", {})
    apply_private_data(
        row_loaded,
        cast("dict[str, Any]", user_private_data) if isinstance(user_private_data, dict) else None,
    )
    row_executor = row_loaded.executor
    if row_executor is None:
        raise RuntimeError(
            f"Batch row variant {spec.variant} has no executable agent or swarm "
            f"(session={session.session_id})"
        )
    logger.info(
        "Session %s batch row %s using variant %s executor %s",
        session.session_id,
        spec.index,
        spec.variant,
        row_loaded.executor_name,
    )
    return row_executor


# MARK: Matrix Runner


async def _execute_batch_matrix_items(
    *,
    session: StudioSession,
    executor: Executor,
    batch_inputs: list[BatchInputSpec],
    base_invoke_kwargs: dict[str, Any],
    structured_output_model: type[BaseModel] | None,
    max_concurrency: int | None,
    mode: str,
    ctx: contextvars.Context,
    logger: LoggerLike,
) -> tuple[list[object], list[int]]:
    from maivn._internal.utils.reporting.context import (
        current_sdk_delivery_mode,
    )

    concurrency = max_concurrency or len(batch_inputs) or 1
    semaphore = asyncio.Semaphore(concurrency)
    row_executors: dict[int, Executor] = {}
    executor_cache: dict[str, Executor] = {}
    for spec in batch_inputs:
        cache_key = spec.variant or "__session__"
        if cache_key not in executor_cache:
            executor_cache[cache_key] = _resolve_row_executor(
                session=session,
                executor=executor,
                spec=spec,
                logger=logger,
            )
        row_executors[spec.index] = executor_cache[cache_key]

    async def _invoke_one(spec: BatchInputSpec) -> tuple[object, int]:
        async with semaphore:
            started = time.time()
            row_executor = row_executors[spec.index]
            invoke_kwargs = dict(base_invoke_kwargs)
            invoke_kwargs.update(spec.invocation or {})
            invoke_kwargs["messages"] = spec.messages

            if structured_output_model:
                if not supports_structured_output_kwarg(row_executor):
                    raise RuntimeError(
                        "Batch matrix structured output requires executors that support "
                        f"structured_output=... (session={session.session_id})"
                    )
                invoke_kwargs["structured_output"] = structured_output_model
                invoke_kwargs.pop("targeted_tools", None)

            def _call_invoke() -> object:
                delivery_token = current_sdk_delivery_mode.set(mode)
                try:
                    return row_executor.invoke(**invoke_kwargs)
                finally:
                    current_sdk_delivery_mode.reset(delivery_token)

            item_ctx = ctx.copy()
            response = await asyncio.to_thread(item_ctx.run, _call_invoke)
            duration_ms = int((time.time() - started) * 1000)
            return response, duration_ms

    pairs = await asyncio.gather(*[_invoke_one(spec) for spec in batch_inputs])
    responses = [pair[0] for pair in pairs]
    durations = [pair[1] for pair in pairs]
    return responses, durations


# MARK: Batch Turn Driver


async def _execute_batch_turn(
    manager: ExecutionManagerLike,
    session: StudioSession,
    *,
    executor: Executor,
    loaded: LoadedApp,
    batch_config: dict[str, Any],
    ctx: contextvars.Context,
    logger: LoggerLike,
) -> BatchTurnResult:
    from maivn._internal.utils.reporting.context import (
        current_sdk_delivery_mode,
    )

    batch_start_time = time.time()
    batch_inputs = _build_batch_inputs(manager, session, batch_config)
    input_texts = [spec.message for spec in batch_inputs]
    pending_items = [_serialize_batch_pending_spec(spec) for spec in batch_inputs]
    max_concurrency = batch_config.get("max_concurrency")
    if not isinstance(max_concurrency, int):
        max_concurrency = None
    async_mode = batch_config.get("async_mode") is not False
    mode = "abatch" if async_mode else "batch"
    turn_number = len([m for m in session.messages if isinstance(m, HumanMessage)])
    batch_id = f"{session.session_id}:turn:{turn_number}"

    await manager.emit_event(
        session,
        "batch_start",
        {
            "session_id": session.session_id,
            "batch_id": batch_id,
            "mode": mode,
            "item_count": len(batch_inputs),
            "max_concurrency": max_concurrency,
            "async_mode": async_mode,
            "inputs": input_texts,
            "items": pending_items,
        },
    )

    structured_output_config = session.metadata.get("structured_output")
    structured_output_model = _resolve_structured_output_model(
        session=session,
        executor=executor,
        structured_output_config=structured_output_config,
        logger=logger,
    )
    invoke_kwargs = _build_base_invoke_kwargs(
        loaded=loaded,
        session=session,
        structured_output_model=structured_output_model,
    )
    invoke_kwargs["thread_id"] = session.thread_id
    invoke_kwargs.pop("messages", None)

    if structured_output_model:
        if not supports_structured_output_kwarg(executor):
            raise RuntimeError(
                "Batch structured output requires an executor that supports "
                f"structured_output=... (session={session.session_id})"
            )
        invoke_kwargs["structured_output"] = structured_output_model

    if structured_output_model and invoke_kwargs.get("targeted_tools"):
        logger.warning(
            "Session %s: ignoring targeted_tools because structured_output is enabled",
            session.session_id,
        )
        invoke_kwargs.pop("targeted_tools", None)

    use_matrix_runner = any(spec.has_row_overrides for spec in batch_inputs)
    batch_message_inputs = [spec.messages for spec in batch_inputs]
    item_durations: list[int | None] = [None] * len(batch_inputs)

    if use_matrix_runner:
        responses, resolved_durations = await _execute_batch_matrix_items(
            session=session,
            executor=executor,
            batch_inputs=batch_inputs,
            base_invoke_kwargs=invoke_kwargs,
            structured_output_model=structured_output_model,
            max_concurrency=max_concurrency,
            mode=mode,
            ctx=ctx,
            logger=logger,
        )
        item_durations = list(resolved_durations)
    elif async_mode:
        delivery_token = current_sdk_delivery_mode.set("abatch")
        try:
            batch_result = executor.abatch(
                batch_message_inputs,
                max_concurrency=max_concurrency,
                **invoke_kwargs,
            )
            if not inspect.isawaitable(batch_result):
                raise RuntimeError(
                    "Executor abatch() returned a non-awaitable result "
                    f"(session={session.session_id})"
                )
            responses = list(await cast("Awaitable[Iterable[object]]", batch_result))
        finally:
            current_sdk_delivery_mode.reset(delivery_token)
    else:
        typed_batch_fn = cast("Callable[..., Iterable[object]]", executor.batch)

        def _call_batch() -> list[object]:
            delivery_token = current_sdk_delivery_mode.set("batch")
            try:
                return list(
                    typed_batch_fn(
                        batch_message_inputs,
                        max_concurrency=max_concurrency,
                        **invoke_kwargs,
                    )
                )
            finally:
                current_sdk_delivery_mode.reset(delivery_token)

        responses = await asyncio.to_thread(ctx.run, _call_batch)

    if len(responses) != len(input_texts):
        raise RuntimeError(
            f"SDK batch returned an unexpected number of responses (session={session.session_id})"
        )

    items = [
        _serialize_batch_response(
            response,
            spec=batch_inputs[index],
            duration_ms=item_durations[index],
        )
        for index, response in enumerate(responses)
    ]
    duration_ms = int((time.time() - batch_start_time) * 1000)
    token_usage = sum_token_usage(items)

    for item in items:
        await manager.emit_event(
            session,
            "batch_item_complete",
            {
                "session_id": session.session_id,
                "batch_id": batch_id,
                **item,
            },
        )

    batch_event_data: dict[str, Any] = {
        "session_id": session.session_id,
        "batch_id": batch_id,
        "mode": mode,
        "status": "completed",
        "item_count": len(items),
        "max_concurrency": max_concurrency,
        "async_mode": async_mode,
        "duration_ms": duration_ms,
        "token_usage": token_usage,
        "items": items,
    }
    await manager.emit_event(session, "batch_complete", batch_event_data)
    return BatchTurnResult(responses=responses, event_data=batch_event_data)


__all__ = [
    "BatchInputSpec",
    "BatchTurnResult",
    "_execute_batch_turn",
]
