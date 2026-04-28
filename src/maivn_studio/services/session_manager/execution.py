"""Execution helpers for session management."""

from __future__ import annotations

import asyncio
import contextvars
import inspect
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from maivn.events import (
    NormalizedEventForwardingState,
    NormalizedStreamState,
    forward_normalized_event,
    normalize_stream_event,
)
from maivn_shared import FINAL_EVENT_NAME
from maivn_shared import SessionResponse as SDKSessionResponse

from .messages import resolve_structured_output_metadata_fallback
from .models import _STUDIO_EVENT_CATEGORIES, SessionStatus, StudioSession, _latest_response_text

# MARK: Capability Helpers


def supports_structured_output_kwarg(executor: Any) -> bool:
    """Return whether the executor accepts a structured_output invoke kwarg."""
    invoke_fn = getattr(executor, "invoke", None)
    if not callable(invoke_fn):
        return False
    try:
        params = inspect.signature(invoke_fn).parameters
    except (TypeError, ValueError):
        return False

    if "structured_output" in params:
        return True

    return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())


async def flush_reporter_events(reporter: Any | None, logger: Any) -> None:
    """Flush buffered reporter output if supported."""
    flush_fn = getattr(reporter, "flush", None)
    if not callable(flush_fn):
        return
    try:
        flush_result = flush_fn()
        if inspect.isawaitable(flush_result):
            await flush_result
    except Exception as exc:
        logger.warning("Failed to flush pending Studio reporter events: %s", exc)


def _build_stream_tool_contract_maps(
    manager: Any,
    executor: Any,
) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
    tool_name_map, tool_metadata_map = manager._build_tool_contract_maps(executor)
    list_tools = getattr(executor, "list_tools", None)
    raw_tools_candidate = list_tools() if callable(list_tools) else []
    if isinstance(raw_tools_candidate, Iterable):
        raw_tools = list(raw_tools_candidate)
    else:
        raw_tools = []

    for tool in raw_tools:
        tool_name = getattr(tool, "name", None)
        if not isinstance(tool_name, str) or not tool_name.strip():
            continue

        normalized_tool_name = tool_name.strip()
        tool_id = getattr(tool, "tool_id", None)
        if not isinstance(tool_id, str) or not tool_id.strip():
            tool_id = getattr(tool, "id", None)
        if not isinstance(tool_id, str) or not tool_id.strip():
            continue

        normalized_tool_id = tool_id.strip()
        metadata = tool_metadata_map.setdefault(
            normalized_tool_id, {"tool_name": normalized_tool_name}
        )
        metadata.setdefault("tool_name", normalized_tool_name)

        tool_type = getattr(tool, "tool_type", None)
        if not isinstance(tool_type, str) or not tool_type.strip():
            tool_type = getattr(tool, "type", None)
        if isinstance(tool_type, str) and tool_type.strip():
            metadata.setdefault("tool_type", tool_type.strip().lower())

        target_agent_id = getattr(tool, "target_agent_id", None)
        if isinstance(target_agent_id, str) and target_agent_id.strip():
            metadata.setdefault("target_agent_id", target_agent_id.strip())

        agent_name = getattr(tool, "agent_name", None)
        if isinstance(agent_name, str) and agent_name.strip():
            metadata.setdefault("agent_name", agent_name.strip())
        elif metadata.get("tool_type") == "agent":
            metadata.setdefault("agent_name", normalized_tool_name)

        swarm_name = getattr(tool, "swarm_name", None)
        if isinstance(swarm_name, str) and swarm_name.strip():
            metadata.setdefault("swarm_name", swarm_name.strip())

        tool_name_map.setdefault(normalized_tool_id, normalized_tool_name)

    return tool_name_map, tool_metadata_map


# MARK: Batch Helpers


@dataclass
class BatchTurnResult:
    responses: list[Any]
    event_data: dict[str, Any]


@dataclass
class BatchInputSpec:
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


def _serialize_structured_result(result: Any) -> Any:
    if result is None:
        return None

    from pydantic import BaseModel

    if isinstance(result, BaseModel):
        return result.model_dump()
    return result


def _serialize_token_usage(token_usage: Any) -> dict[str, int] | None:
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


def _sum_token_usage(items: list[dict[str, Any]]) -> dict[str, int] | None:
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


def _serialize_batch_response(
    result: Any,
    *,
    spec: BatchInputSpec,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    responses = getattr(result, "responses", None)
    response_text = _latest_response_text(responses)
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
        "result": _serialize_structured_result(getattr(result, "result", None)),
        "duration_ms": duration_ms,
        "token_usage": _serialize_token_usage(getattr(result, "token_usage", None)),
    }
    return {key: value for key, value in item.items() if value is not None}


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
    fallback_metadata = resolve_structured_output_metadata_fallback(
        loaded_demo=loaded,
        structured_output_model=structured_output_model,
        user_invoke_kwargs=user_invoke_kwargs,
    )
    if fallback_metadata is not None:
        invoke_kwargs["metadata"] = fallback_metadata
    if user_invoke_kwargs:
        invoke_kwargs.update(user_invoke_kwargs)

    invoke_kwargs.pop("verbose", None)
    return invoke_kwargs


def _resolve_row_executor(
    *,
    session: StudioSession,
    executor: Any,
    spec: BatchInputSpec,
    logger: Any,
) -> Any:
    if not spec.variant or spec.variant == session.variant:
        return executor

    if spec.variant not in session.demo_config.variants:
        raise ValueError(f"Unknown batch row variant: {spec.variant}")

    from maivn_studio.services.demo_loader.loader import get_demo_loader
    from maivn_studio.services.session_manager.private_data import apply_private_data

    row_loaded = get_demo_loader().load(
        session.demo_config,
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
    token_usage = _sum_token_usage(items)

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


# MARK: Replay Ownership

_REPORTER_REPLAY_EVENT_NAMES = frozenset(
    {
        "assistant_chunk",
        "system_tool_chunk",
    }
)
_BRIDGE_REPLAY_EVENT_NAMES = frozenset({"interrupt_required"})


def _should_replay_event_to_reporter(event_name: str) -> bool:
    return event_name in _REPORTER_REPLAY_EVENT_NAMES


def _should_replay_event_to_bridge(event_name: str) -> bool:
    return event_name in _BRIDGE_REPLAY_EVENT_NAMES


def _replay_normalized_events(
    normalized_events: list[Any],
    *,
    reporter: Any,
    bridge: Any | None,
    loop: asyncio.AbstractEventLoop,
    forwarding_state: NormalizedEventForwardingState,
) -> None:
    for normalized_event in normalized_events:
        replay_reporter = (
            reporter if _should_replay_event_to_reporter(normalized_event.event_name) else None
        )
        replay_bridge = (
            bridge if _should_replay_event_to_bridge(normalized_event.event_name) else None
        )

        if replay_reporter is None and replay_bridge is None:
            continue

        future = asyncio.run_coroutine_threadsafe(
            forward_normalized_event(
                normalized_event,
                reporter=replay_reporter,
                bridge=replay_bridge,
                state=forwarding_state,
            ),
            loop,
        )
        future.result()


# MARK: Session Execution


async def execute_session(manager: Any, session: StudioSession, logger: Any) -> None:
    """Execute a Studio session in the background."""
    import time as time_module

    reporter_token: contextvars.Token | None = None
    reporter: Any | None = None
    try:
        loaded = session._loaded_demo
        if not loaded or not loaded.executor:
            raise ValueError("No executor available")

        executor = loaded.executor

        from maivn._internal.utils.reporting.context import (
            current_reporter,
            current_sdk_delivery_mode,
        )

        from ..event_bridge import get_event_bridge
        from ..studio_reporter.reporter import StudioReporter

        bridge = get_event_bridge(session.session_id)
        loop = asyncio.get_running_loop()
        logger.info("Session %s: bridge=%s", session.session_id, bridge is not None)

        if bridge is not None and bridge._closed:
            bridge.reopen()

        ctx = contextvars.copy_context()
        if bridge:
            reporter = StudioReporter(bridge, loop)
            reporter_token = current_reporter.set(reporter)
            ctx = contextvars.copy_context()
            logger.info("Session %s: StudioReporter set in context", session.session_id)
        else:
            logger.warning("Session %s: No bridge found, reporter not set", session.session_id)

        await manager._emit_session_start_event(
            session,
            executor=executor,
            executor_type=loaded.executor_type,
        )

        while True:
            turn_start_time = time_module.time()
            structured_output_config = session.metadata.get("structured_output")
            batch_config = session.metadata.get("batch_config")

            def _invoke_executor(
                structured_output_config: dict[str, Any] | None = structured_output_config,
            ) -> Any:
                def _call_with_delivery_mode(
                    delivery_mode: str,
                    fn: Callable[..., Any],
                    **kwargs: Any,
                ) -> Any:
                    delivery_token = current_sdk_delivery_mode.set(delivery_mode)
                    try:
                        return fn(**kwargs)
                    finally:
                        current_sdk_delivery_mode.reset(delivery_token)

                event_builder = getattr(executor, "events", None)
                if callable(event_builder):
                    event_invocable = event_builder(
                        include=_STUDIO_EVENT_CATEGORIES,
                        auto_verbose=False,
                    )
                else:
                    logger.warning(
                        "Session %s: executor %s has no events() builder; using legacy path",
                        session.session_id,
                        type(executor).__name__,
                    )
                    event_invocable = executor

                structured_output_model: type[Any] | None = None
                if structured_output_config:
                    tool_name = structured_output_config.get("tool_name")
                    if tool_name:
                        from maivn._internal.core.entities import ModelTool

                        model_class = None
                        for tool in executor.list_tools():
                            if tool.name == tool_name:
                                if isinstance(tool, ModelTool):
                                    model_class = tool.model
                                break

                        if model_class:
                            structured_output_model = model_class
                            logger.info(
                                "Session %s using structured_output with model: %s (from tool: %s)",
                                session.session_id,
                                model_class.__name__,
                                tool_name,
                            )
                        else:
                            logger.warning(
                                "Session %s: Tool %s not found or is not a ModelTool, "
                                "ignoring structured_output config",
                                session.session_id,
                                tool_name,
                            )
                            session.metadata["structured_output_warning"] = (
                                f'Tool "{tool_name}" not found or is not a ModelTool'
                            )

                invoke_kwargs: dict[str, Any] = {
                    "messages": session.messages,
                    "thread_id": session.thread_id,
                }

                user_invoke_kwargs = session.metadata.get("invocation_kwargs")
                fallback_metadata = resolve_structured_output_metadata_fallback(
                    loaded_demo=loaded,
                    structured_output_model=structured_output_model,
                    user_invoke_kwargs=user_invoke_kwargs,
                )
                if fallback_metadata is not None:
                    invoke_kwargs["metadata"] = fallback_metadata
                if user_invoke_kwargs:
                    invoke_kwargs.update(user_invoke_kwargs)

                invoke_kwargs.pop("verbose", None)

                if structured_output_model and invoke_kwargs.get("targeted_tools"):
                    logger.warning(
                        "Session %s: ignoring targeted_tools because structured_output is enabled",
                        session.session_id,
                    )
                    invoke_kwargs.pop("targeted_tools", None)

                event_invoke_fn = getattr(event_invocable, "invoke", None)
                if not callable(event_invoke_fn):
                    raise RuntimeError(
                        f"Executor does not support invoke() (session={session.session_id})"
                    )

                if structured_output_model and supports_structured_output_kwarg(executor):
                    invoke_kwargs["structured_output"] = structured_output_model
                    return _call_with_delivery_mode("invoke", event_invoke_fn, **invoke_kwargs)

                if structured_output_model:
                    structured_builder = getattr(event_invocable, "structured_output", None)
                    use_legacy_structured_path = not callable(structured_builder)
                    if use_legacy_structured_path:
                        structured_builder = getattr(executor, "structured_output", None)
                    if not callable(structured_builder):
                        raise RuntimeError(
                            "Executor does not support structured_output() builder "
                            f"(session={session.session_id})"
                        )

                    structured_invocable = structured_builder(structured_output_model)
                    invoke_kwargs.pop("targeted_tools", None)

                    if use_legacy_structured_path and callable(event_builder):
                        from maivn._internal.utils.reporting.terminal_reporter import event_router

                        base_reporter = current_reporter.get()
                        if base_reporter is not None:
                            event_router_reporter_cls = getattr(
                                event_router,
                                "EventRouterReporter",
                                None,
                            )
                            if not callable(event_router_reporter_cls):
                                raise RuntimeError(
                                    "EventRouterReporter unavailable for legacy structured output "
                                    f"(session={session.session_id})"
                                )
                            routed_reporter = cast(Any, event_router_reporter_cls)(
                                base_reporter,
                                include=_STUDIO_EVENT_CATEGORIES,
                            )
                            routed_token = current_reporter.set(cast(Any, routed_reporter))
                            try:
                                structured_invoke_fn = getattr(structured_invocable, "invoke", None)
                                if not callable(structured_invoke_fn):
                                    raise RuntimeError(
                                        "Structured invocable does not support invoke() "
                                        f"(session={session.session_id})"
                                    )
                                return _call_with_delivery_mode(
                                    "invoke",
                                    structured_invoke_fn,
                                    **invoke_kwargs,
                                )
                            finally:
                                current_reporter.reset(routed_token)

                    structured_invoke_fn = getattr(structured_invocable, "invoke", None)
                    if not callable(structured_invoke_fn):
                        raise RuntimeError(
                            "Structured invocable does not support invoke() "
                            f"(session={session.session_id})"
                        )
                    return _call_with_delivery_mode("invoke", structured_invoke_fn, **invoke_kwargs)

                should_stream = invoke_kwargs.get("stream_response", True) is not False
                stream_fn = getattr(executor, "stream", None)
                if should_stream and callable(stream_fn):
                    event_stream_fn = getattr(event_invocable, "stream", None)
                    if not callable(event_stream_fn):
                        raise RuntimeError(
                            f"Executor does not support stream() (session={session.session_id})"
                        )
                    stream_result = _call_with_delivery_mode(
                        "stream", event_stream_fn, **invoke_kwargs
                    )
                    if not isinstance(stream_result, Iterable):
                        raise RuntimeError(
                            "SDK stream() returned a non-iterable result "
                            f"(session={session.session_id})"
                        )
                    normalized_stream_state = NormalizedStreamState()
                    forwarding_state = NormalizedEventForwardingState()
                    tool_name_map, tool_metadata_map = _build_stream_tool_contract_maps(
                        manager,
                        executor,
                    )
                    final_payload: dict[str, Any] | None = None
                    for event in stream_result:
                        normalized_events = normalize_stream_event(
                            event,
                            state=normalized_stream_state,
                            default_agent_name=executor.name
                            if loaded.executor_type == "agent"
                            else None,
                            default_swarm_name=executor.name
                            if loaded.executor_type == "swarm"
                            else None,
                            tool_name_map=tool_name_map,
                            tool_metadata_map=tool_metadata_map,
                        )
                        if reporter is not None:
                            _replay_normalized_events(
                                normalized_events,
                                reporter=reporter,
                                bridge=bridge,
                                loop=loop,
                                forwarding_state=forwarding_state,
                            )

                        payload = getattr(event, "payload", None)
                        if isinstance(payload, dict) and (
                            getattr(event, "name", "") == FINAL_EVENT_NAME
                            or payload.get("event_name") == "final"
                        ):
                            final_payload = payload
                    if final_payload is None:
                        raise RuntimeError(
                            "SDK stream completed without a final payload event "
                            f"(session={session.session_id})"
                        )
                    return SDKSessionResponse.model_validate(final_payload)

                return _call_with_delivery_mode("invoke", event_invoke_fn, **invoke_kwargs)

            if isinstance(batch_config, dict):
                result = await _execute_batch_turn(
                    manager,
                    session,
                    executor=executor,
                    loaded=loaded,
                    batch_config=batch_config,
                    ctx=ctx,
                    logger=logger,
                )
            else:
                result = await asyncio.to_thread(ctx.run, _invoke_executor)
            await flush_reporter_events(reporter, logger)

            batch_event_data: dict[str, Any] | None = None
            if isinstance(result, BatchTurnResult):
                session.result = result.responses
                response = ""
                structured_result = None
                batch_event_data = result.event_data
            else:
                session.result = result
                response = _latest_response_text(getattr(result, "responses", None))
                if response is None:
                    response = ""
                structured_result = _serialize_structured_result(getattr(result, "result", None))
            session.messages.append(AIMessage(content=response))

            turn_duration_ms = int((time_module.time() - turn_start_time) * 1000)

            token_usage = (
                batch_event_data.get("token_usage")
                if batch_event_data
                else _serialize_token_usage(getattr(result, "token_usage", None))
            )

            queued_message_count = session.queued_message_count
            session.status = (
                SessionStatus.RUNNING if queued_message_count > 0 else SessionStatus.READY
            )

            turn_event_data: dict[str, Any] = {
                "session_id": session.session_id,
                "turn_number": len([m for m in session.messages if isinstance(m, HumanMessage)]),
                "responses": [response] if isinstance(response, str) and response.strip() else [],
                "result": structured_result,
                "can_continue": True,
                "duration_ms": turn_duration_ms,
                "token_usage": token_usage,
                "queued_message_count": queued_message_count,
            }
            if batch_event_data is not None:
                turn_event_data["batch"] = batch_event_data
            so_warning = session.metadata.pop("structured_output_warning", None)
            if so_warning:
                turn_event_data["structured_output_warning"] = so_warning

            await manager._emit_event(session, "turn_complete", turn_event_data)

            if queued_message_count <= 0:
                logger.info(
                    "Session %s turn completed, ready for more messages",
                    session.session_id,
                )
                break

            consumed_queued_message_count = manager._consume_queued_messages(session)
            await manager._emit_session_start_event(
                session,
                executor=executor,
                executor_type=loaded.executor_type,
                consumed_queued_message_count=consumed_queued_message_count,
            )
            logger.info(
                "Session %s continuing with %d queued message(s)",
                session.session_id,
                consumed_queued_message_count,
            )

    except asyncio.CancelledError:
        logger.info("Session %s cancelled", session.session_id)
        raise

    except Exception as exc:
        await flush_reporter_events(reporter, logger)
        session.status = SessionStatus.FAILED
        session.error = str(exc)
        session.completed_at = datetime.now()

        batch_config = session.metadata.get("batch_config")
        if isinstance(batch_config, dict):
            raw_rows = batch_config.get("rows")
            if not isinstance(raw_rows, list):
                raw_rows = []
            failed_items: list[dict[str, Any]] = []
            for index, row in enumerate(raw_rows):
                if not isinstance(row, dict):
                    continue
                input_text = str(row.get("message", "")).strip()
                if not input_text:
                    continue
                failed_items.append(
                    {
                        "index": index,
                        "label": row.get("label"),
                        "input": input_text,
                        "variant": row.get("variant"),
                        "model": row.get("model"),
                        "reasoning": row.get("reasoning"),
                        "status": "failed",
                        "error": str(exc),
                        "responses": [],
                        "response": "",
                        "result": None,
                        "token_usage": None,
                    }
                )
            if not failed_items:
                raw_messages = batch_config.get("messages")
                if not isinstance(raw_messages, list):
                    raw_messages = []
                failed_items = [
                    {
                        "index": index,
                        "input": input_text,
                        "status": "failed",
                        "error": str(exc),
                        "responses": [],
                        "response": "",
                        "result": None,
                        "token_usage": None,
                    }
                    for index, input_text in enumerate(
                        item.strip()
                        for item in raw_messages
                        if isinstance(item, str) and item.strip()
                    )
                ]
            batch_id = (
                f"{session.session_id}:turn:"
                f"{len([m for m in session.messages if isinstance(m, HumanMessage)])}"
            )
            await manager._emit_event(
                session,
                "batch_complete",
                {
                    "session_id": session.session_id,
                    "batch_id": batch_id,
                    "mode": "abatch" if batch_config.get("async_mode") is not False else "batch",
                    "status": "failed",
                    "item_count": len(failed_items),
                    "max_concurrency": batch_config.get("max_concurrency"),
                    "async_mode": batch_config.get("async_mode") is not False,
                    "error": str(exc),
                    "items": failed_items,
                },
            )

        await manager._emit_event(
            session,
            "error",
            {
                "session_id": session.session_id,
                "error": str(exc),
            },
        )

        logger.error("Session %s failed: %s", session.session_id, exc)
    finally:
        if reporter_token is not None:
            from maivn._internal.utils.reporting.context import current_reporter

            current_reporter.reset(reporter_token)
