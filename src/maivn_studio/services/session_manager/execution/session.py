"""Top-level ``execute_session`` orchestration.

Owns the turn loop: bridge + reporter wiring, batch vs. invoke vs. stream
dispatch, response capture, and the failure paths that emit batch-complete
records when a batch turn raises.
"""

from __future__ import annotations

import asyncio
import contextvars
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from maivn.events import (
    NormalizedEventForwardingState,
    NormalizedStreamState,
    normalize_stream_event,
)
from maivn_shared import FINAL_EVENT_NAME
from maivn_shared import SessionResponse as SDKSessionResponse

from ..messages import resolve_structured_output_invocation_fallbacks
from ..models import STUDIO_EVENT_CATEGORIES, SessionStatus, StudioSession, latest_response_text
from .batch import BatchTurnResult, _execute_batch_turn
from .capabilities import (
    build_stream_tool_contract_maps,
    flush_reporter_events,
    supports_structured_output_kwarg,
    wait_for_event_subscriber,
)
from .replay import _replay_normalized_events
from .serialization import serialize_structured_result, serialize_token_usage

# MARK: Session Execution


def _build_invocation_messages(messages: list[BaseMessage]) -> list[BaseMessage]:
    current_turn_start = _current_turn_start_index(messages)
    return [
        _prepare_invocation_message(message, keep_attachments=index >= current_turn_start)
        for index, message in enumerate(messages)
    ]


def _current_turn_start_index(messages: list[BaseMessage]) -> int:
    for index in range(len(messages) - 1, -1, -1):
        if isinstance(messages[index], AIMessage):
            return index + 1
    return 0


def _prepare_invocation_message(
    message: BaseMessage,
    *,
    keep_attachments: bool,
) -> BaseMessage:
    if keep_attachments:
        return message

    additional_kwargs = getattr(message, "additional_kwargs", None)
    if not isinstance(additional_kwargs, dict) or "attachments" not in additional_kwargs:
        return message

    sanitized_kwargs = dict(additional_kwargs)
    sanitized_kwargs.pop("attachments", None)
    return message.model_copy(update={"additional_kwargs": sanitized_kwargs}, deep=True)


async def execute_session(manager: Any, session: StudioSession, logger: Any) -> None:
    """Execute a Studio session in the background."""
    import time as time_module

    reporter_token: contextvars.Token | None = None
    reporter: Any | None = None
    try:
        loaded = session._loaded_app
        if not loaded or not loaded.executor:
            raise ValueError("No executor available")

        executor = loaded.executor

        from maivn._internal.utils.reporting.context import (
            current_reporter,
            current_sdk_delivery_mode,
        )

        from ...event_bridge import get_event_bridge
        from ...studio_reporter.reporter import StudioReporter

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

        await wait_for_event_subscriber(session=session, bridge=bridge, logger=logger)

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
                        include=STUDIO_EVENT_CATEGORIES,
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
                    "messages": _build_invocation_messages(session.messages),
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
                                include=STUDIO_EVENT_CATEGORIES,
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
                    tool_name_map, tool_metadata_map = build_stream_tool_contract_maps(
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
                response = latest_response_text(getattr(result, "responses", None))
                if response is None:
                    response = ""
                structured_result = serialize_structured_result(getattr(result, "result", None))
            session.messages.append(AIMessage(content=response))

            turn_duration_ms = int((time_module.time() - turn_start_time) * 1000)

            token_usage = (
                batch_event_data.get("token_usage")
                if batch_event_data
                else serialize_token_usage(getattr(result, "token_usage", None))
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
            await wait_for_event_subscriber(session=session, bridge=bridge, logger=logger)

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

        logger.exception("Session %s failed", session.session_id)
    finally:
        if reporter_token is not None:
            from maivn._internal.utils.reporting.context import current_reporter

            current_reporter.reset(reporter_token)


__all__ = ["execute_session"]
