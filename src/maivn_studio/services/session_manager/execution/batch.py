"""Batch invocation execution for Studio sessions.

Implements the batch turn loop that fans out per-row invocations across the
SDK's ``batch`` / ``abatch`` paths or a per-row matrix runner for rows that
need their own variant + private data context.

The matrix runner exists because the SDK's bulk batch APIs assume one shared
executor; rows with their own ``variant`` need a freshly reloaded app, which
means each row gets its own executor instance.
"""

from __future__ import annotations

import asyncio
import contextvars
import inspect
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from typing import Any, cast

from langchain_core.messages import BaseMessage, HumanMessage

from ..messages import resolve_structured_output_invocation_fallbacks
from ..models import StudioSession, latest_response_text
from .capabilities import supports_structured_output_kwarg
from .serialization import (
    serialize_structured_result,
    serialize_token_usage,
    sum_token_usage,
)

# MARK: Batch Result Models


@dataclass
class BatchTurnResult:
    """Aggregated outcome of a single batch turn: per-item responses + the event payload."""

    responses: list[Any]
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


# MARK: Item Serialization


def _serialize_batch_response(
    result: Any,
    *,
    spec: BatchInputSpec,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    responses = getattr(result, "responses", None)
    response_text = latest_response_text(responses)
    if response_text is None:
        raw_response = getattr(result, "response", None)
        response_text = raw_response if isinstance(raw_response, str) else ""

    item = {
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
    item = {
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
    manager: Any,
    session: StudioSession,
    batch_config: dict[str, Any],
) -> list[BatchInputSpec]:
    raw_messages = batch_config.get("messages")
    if not isinstance(raw_messages, list):
        raw_messages = []
    messages = [item.strip() for item in raw_messages if isinstance(item, str) and item.strip()]

    raw_rows = batch_config.get("rows")
    if not isinstance(raw_rows, list):
        raw_rows = []
    rows: list[dict[str, Any]] = [
        row for row in raw_rows if isinstance(row, dict) and str(row.get("message", "")).strip()
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
    attachments = batch_config.get("attachments")
    if not isinstance(attachments, list):
        attachments = None

    batch_inputs: list[BatchInputSpec] = []
    for index, row in enumerate(rows):
        message = str(row.get("message", "")).strip()
        row_messages = list(base_messages)
        system_message = row.get("system_message")
        if isinstance(system_message, str) and system_message.strip():
            row_messages.append(manager._create_message(system_message.strip(), "system"))
        row_messages.append(
            manager._create_message(
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
                item.strip() for item in targeted_tools if isinstance(item, str) and item.strip()
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
    executor: Any,
    structured_output_config: dict[str, Any] | None,
    logger: Any,
) -> type[Any] | None:
    if not structured_output_config:
        return None

    tool_name = structured_output_config.get("tool_name")
    if not tool_name:
        return None

    from maivn._internal.core.entities import ModelTool

    model_class = None
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
    loaded: Any,
    session: StudioSession,
    structured_output_model: type[Any] | None,
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
    if user_invoke_kwargs:
        invoke_kwargs.update(user_invoke_kwargs)

    invoke_kwargs.pop("verbose", None)
    return invoke_kwargs


# MARK: Per-Row Executor Resolution


def _resolve_row_executor(
    *,
    session: StudioSession,
    executor: Any,
    spec: BatchInputSpec,
    logger: Any,
) -> Any:
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
    apply_private_data(row_loaded, user_private_data)
    if not row_loaded.has_executor:
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
    return row_loaded.executor


# MARK: Matrix Runner


async def _execute_batch_matrix_items(
    *,
    session: StudioSession,
    executor: Any,
    batch_inputs: list[BatchInputSpec],
    base_invoke_kwargs: dict[str, Any],
    structured_output_model: type[Any] | None,
    max_concurrency: int | None,
    mode: str,
    ctx: contextvars.Context,
    logger: Any,
) -> tuple[list[Any], list[int]]:
    import time as time_module

    from maivn._internal.utils.reporting.context import current_sdk_delivery_mode

    concurrency = max_concurrency or len(batch_inputs) or 1
    semaphore = asyncio.Semaphore(concurrency)
    row_executors: dict[int, Any] = {}
    executor_cache: dict[str, Any] = {}
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

    async def _invoke_one(spec: BatchInputSpec) -> tuple[Any, int]:
        async with semaphore:
            started = time_module.time()
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

            invoke_fn = getattr(row_executor, "invoke", None)
            if not callable(invoke_fn):
                raise RuntimeError(
                    f"Batch row executor does not support invoke() (session={session.session_id})"
                )

            def _call_invoke() -> Any:
                delivery_token = current_sdk_delivery_mode.set(mode)
                try:
                    return invoke_fn(**invoke_kwargs)
                finally:
                    current_sdk_delivery_mode.reset(delivery_token)

            item_ctx = ctx.copy()
            response = await asyncio.to_thread(item_ctx.run, _call_invoke)
            duration_ms = int((time_module.time() - started) * 1000)
            return response, duration_ms

    pairs = await asyncio.gather(*[_invoke_one(spec) for spec in batch_inputs])
    responses = [pair[0] for pair in pairs]
    durations = [pair[1] for pair in pairs]
    return responses, durations


# MARK: Batch Turn Driver


async def _execute_batch_turn(
    manager: Any,
    session: StudioSession,
    *,
    executor: Any,
    loaded: Any,
    batch_config: dict[str, Any],
    ctx: contextvars.Context,
    logger: Any,
) -> BatchTurnResult:
    import time as time_module

    from maivn._internal.utils.reporting.context import current_sdk_delivery_mode

    batch_start_time = time_module.time()
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

    await manager._emit_event(
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
        item_durations = cast(list[int | None], resolved_durations)
    elif async_mode:
        batch_fn = getattr(executor, "abatch", None)
        if not callable(batch_fn):
            raise RuntimeError(f"Executor does not support abatch() (session={session.session_id})")
        typed_batch_fn = cast(Callable[..., Any], batch_fn)

        delivery_token = current_sdk_delivery_mode.set("abatch")
        try:
            batch_result = typed_batch_fn(
                batch_message_inputs,
                max_concurrency=max_concurrency,
                **invoke_kwargs,
            )
            if not inspect.isawaitable(batch_result):
                raise RuntimeError(
                    "Executor abatch() returned a non-awaitable result "
                    f"(session={session.session_id})"
                )
            responses = list(await cast(Awaitable[Iterable[Any]], batch_result))
        finally:
            current_sdk_delivery_mode.reset(delivery_token)
    else:
        batch_fn = getattr(executor, "batch", None)
        if not callable(batch_fn):
            raise RuntimeError(f"Executor does not support batch() (session={session.session_id})")
        typed_batch_fn = cast(Callable[..., Iterable[Any]], batch_fn)

        def _call_batch() -> list[Any]:
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
    duration_ms = int((time_module.time() - batch_start_time) * 1000)
    token_usage = sum_token_usage(items)

    for item in items:
        await manager._emit_event(
            session,
            "batch_item_complete",
            {
                "session_id": session.session_id,
                "batch_id": batch_id,
                **item,
            },
        )

    batch_event_data = {
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
    await manager._emit_event(session, "batch_complete", batch_event_data)
    return BatchTurnResult(responses=responses, event_data=batch_event_data)


__all__ = [
    "BatchInputSpec",
    "BatchTurnResult",
    "_execute_batch_turn",
]
