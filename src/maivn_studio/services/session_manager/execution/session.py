"""Top-level ``execute_session`` orchestration.

Owns the turn loop: bridge + reporter wiring, batch vs. invoke vs. stream
dispatch, response capture, and the failure paths that emit batch-complete
records when a batch turn raises.
"""

# pyright: strict
from __future__ import annotations

import asyncio
import contextvars
import time
from collections.abc import Callable, Iterable
from contextvars import Token
from datetime import datetime
from typing import Any, cast

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from maivn._internal.utils.reporting.context import (
    current_reporter,
    current_sdk_delivery_mode,
)
from maivn._internal.utils.reporting.terminal_reporter import (
    BaseReporter,
)
from maivn.events import (
    EventBridge,
    NormalizedEventForwardingState,
    NormalizedStreamState,
    RawSSEEvent,
    normalize_stream_event,
)
from maivn_shared import FINAL_EVENT_NAME
from maivn_shared import SessionResponse as SDKSessionResponse

from ...app_loader.models import Executor, LoadedApp
from ...event_bridge import get_event_bridge
from ...studio_reporter.reporter import StudioReporter
from ..messages import resolve_structured_output_invocation_fallbacks
from ..models import STUDIO_EVENT_CATEGORIES, SessionStatus, StudioSession, latest_response_text
from .batch import BatchTurnResult, _execute_batch_turn
from .capabilities import (
    LoggerLike,
    auto_resolve_structured_output_model,
    build_stream_tool_contract_maps,
    flush_reporter_events,
    wait_for_event_subscriber,
)
from .protocols import ExecutionManagerLike
from .replay import replay_normalized_events
from .serialization import serialize_structured_result, serialize_token_usage

# MARK: Invocation Message Preparation


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

    # langchain_core types ``additional_kwargs`` as a bare ``dict``; treat it as the
    # documented ``dict[str, Any]`` mapping at this boundary.
    additional_kwargs = cast("dict[str, Any]", message.additional_kwargs)
    if "attachments" not in additional_kwargs:
        return message

    sanitized_kwargs = dict(additional_kwargs)
    sanitized_kwargs.pop("attachments", None)
    return message.model_copy(update={"additional_kwargs": sanitized_kwargs}, deep=True)


# MARK: Session Execution


async def execute_session(
    manager: ExecutionManagerLike,
    session: StudioSession,
    logger: LoggerLike,
) -> None:
    """Execute a Studio session in the background."""
    reporter_token: Token[BaseReporter | None] | None = None
    reporter: StudioReporter | None = None
    try:
        loaded = session.loaded_app
        if loaded is None or loaded.executor is None:
            raise ValueError("No executor available")

        executor = loaded.executor

        bridge = get_event_bridge(session.session_id)
        loop = asyncio.get_running_loop()
        logger.info("Session %s: bridge=%s", session.session_id, bridge is not None)

        if bridge is not None and bridge.stream_is_closed:
            bridge.reopen()

        ctx = contextvars.copy_context()
        if bridge is not None:
            reporter = StudioReporter(bridge, loop)
            reporter_token = current_reporter.set(reporter)
            ctx = contextvars.copy_context()
            logger.info("Session %s: StudioReporter set in context", session.session_id)
        else:
            logger.warning("Session %s: No bridge found, reporter not set", session.session_id)

        await wait_for_event_subscriber(session=session, bridge=bridge, logger=logger)

        await manager.emit_session_start_event(
            session,
            executor=executor,
            executor_type=loaded.executor_type,
        )

        while True:
            turn_start_time = time.time()
            structured_output_config = session.metadata.get("structured_output")
            batch_config = session.metadata.get("batch_config")

            def _invoke_executor(
                structured_output_config: object = structured_output_config,
            ) -> object:
                return _run_invoke_turn(
                    session=session,
                    executor=executor,
                    loaded=loaded,
                    reporter=reporter,
                    bridge=bridge,
                    loop=loop,
                    manager=manager,
                    logger=logger,
                    structured_output_config=structured_output_config,
                )

            if isinstance(batch_config, dict):
                result: object = await _execute_batch_turn(
                    manager,
                    session,
                    executor=executor,
                    loaded=loaded,
                    batch_config=cast("dict[str, Any]", batch_config),
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
                structured_result: object = None
                batch_event_data = result.event_data
            else:
                session.result = result
                response = latest_response_text(getattr(result, "responses", None)) or ""
                structured_result = serialize_structured_result(getattr(result, "result", None))
            session.messages.append(AIMessage(content=response))

            turn_duration_ms = int((time.time() - turn_start_time) * 1000)

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
                "responses": [response] if response.strip() else [],
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

            await manager.emit_event(session, "turn_complete", turn_event_data)

            if queued_message_count <= 0:
                logger.info(
                    "Session %s turn completed, ready for more messages",
                    session.session_id,
                )
                break

            consumed_queued_message_count = manager.consume_queued_messages(session)
            await wait_for_event_subscriber(session=session, bridge=bridge, logger=logger)

            await manager.emit_session_start_event(
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

    except Exception as exc:  # noqa: BLE001 - failures are recorded and emitted, never re-raised
        await flush_reporter_events(reporter, logger)
        await _emit_failure_events(manager, session, exc, logger)
    finally:
        if reporter_token is not None:
            current_reporter.reset(reporter_token)


# MARK: Invoke Turn


def _run_invoke_turn(
    *,
    session: StudioSession,
    executor: Executor,
    loaded: LoadedApp,
    reporter: StudioReporter | None,
    bridge: EventBridge | None,
    loop: asyncio.AbstractEventLoop,
    manager: ExecutionManagerLike,
    logger: LoggerLike,
    structured_output_config: object,
) -> object:
    """Run a single non-batch turn: build kwargs, dispatch invoke or stream."""
    event_invocable = executor.events(
        include=STUDIO_EVENT_CATEGORIES,
        auto_verbose=False,
    )

    structured_output_model = _resolve_structured_output_model(
        session=session,
        executor=executor,
        structured_output_config=structured_output_config,
        logger=logger,
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
    if isinstance(user_invoke_kwargs, dict):
        invoke_kwargs.update(cast("dict[str, Any]", user_invoke_kwargs))

    invoke_kwargs.pop("verbose", None)

    if loaded.executor_type == "swarm" and invoke_kwargs.get("targeted_tools"):
        logger.warning(
            "Session %s: ignoring targeted_tools because the executor is a swarm "
            "(swarms do not support tool targeting)",
            session.session_id,
        )
        invoke_kwargs.pop("targeted_tools", None)

    if structured_output_model and invoke_kwargs.get("targeted_tools"):
        logger.warning(
            "Session %s: ignoring targeted_tools because structured_output is enabled",
            session.session_id,
        )
        invoke_kwargs.pop("targeted_tools", None)

    if structured_output_model:
        # Pure structured_output() runs its own schema path; forcing normal final-tool
        # selection can reject valid schema results when no runtime final tool completed.
        invoke_kwargs["force_final_tool"] = False

    if structured_output_model:
        return _invoke_structured_output(
            session=session,
            executor=executor,
            event_invocable=event_invocable,
            structured_output_model=structured_output_model,
            invoke_kwargs=invoke_kwargs,
        )

    should_stream = invoke_kwargs.get("stream_response", True) is not False
    if should_stream:
        return _invoke_stream(
            session=session,
            executor=executor,
            loaded=loaded,
            event_invocable=event_invocable,
            reporter=reporter,
            bridge=bridge,
            loop=loop,
            manager=manager,
            invoke_kwargs=invoke_kwargs,
        )

    return _call_with_delivery_mode("invoke", event_invocable.invoke, **invoke_kwargs)


def _call_with_delivery_mode(
    delivery_mode: str,
    fn: Callable[..., object],
    **kwargs: Any,
) -> object:
    delivery_token = current_sdk_delivery_mode.set(delivery_mode)
    try:
        return fn(**kwargs)
    finally:
        current_sdk_delivery_mode.reset(delivery_token)


def _resolve_structured_output_model(
    *,
    session: StudioSession,
    executor: Executor,
    structured_output_config: object,
    logger: LoggerLike,
) -> type[Any] | None:
    if not isinstance(structured_output_config, dict):
        return None
    tool_name: object = cast("dict[str, Any]", structured_output_config).get("tool_name")
    if not tool_name:
        # Structured output was enabled without an explicit schema source. Auto-resolve
        # the app's final/sole model tool so flipping the toggle "just works", instead of
        # silently falling through to the normal synthesizing path.
        return auto_resolve_structured_output_model(
            session=session, executor=executor, logger=logger
        )

    from maivn._internal.core.entities import (
        ModelTool,
    )

    model_class: type[Any] | None = None
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


def _invoke_structured_output(
    *,
    session: StudioSession,
    executor: Executor,
    event_invocable: object,
    structured_output_model: type[Any],
    invoke_kwargs: dict[str, Any],
) -> object:
    structured_builder = getattr(event_invocable, "structured_output", None)
    use_legacy_structured_path = not callable(structured_builder)
    if use_legacy_structured_path:
        structured_builder = executor.structured_output
    if not callable(structured_builder):
        raise RuntimeError(
            f"Executor does not support structured_output() builder (session={session.session_id})"
        )

    structured_invocable = cast("Callable[..., object]", structured_builder)(
        structured_output_model
    )
    invoke_kwargs.pop("targeted_tools", None)

    if use_legacy_structured_path:
        routed = _invoke_structured_output_via_router(
            session=session,
            structured_invocable=structured_invocable,
            invoke_kwargs=invoke_kwargs,
        )
        if routed is not _ROUTER_SKIPPED:
            return routed

    return _invoke_structured_invocable(session, structured_invocable, invoke_kwargs)


def _invoke_structured_invocable(
    session: StudioSession,
    structured_invocable: object,
    invoke_kwargs: dict[str, Any],
) -> object:
    structured_invoke_fn = getattr(structured_invocable, "invoke", None)
    if not callable(structured_invoke_fn):
        raise RuntimeError(
            f"Structured invocable does not support invoke() (session={session.session_id})"
        )
    return _call_with_delivery_mode("invoke", structured_invoke_fn, **invoke_kwargs)


# Sentinel: the legacy event-router path was not taken (no active base reporter),
# so the caller should fall through to the direct structured invoke.
_ROUTER_SKIPPED: object = object()


def _invoke_structured_output_via_router(
    *,
    session: StudioSession,
    structured_invocable: object,
    invoke_kwargs: dict[str, Any],
) -> object:
    """Invoke through an EventRouterReporter when a base reporter is active.

    Returns :data:`_ROUTER_SKIPPED` when no base reporter is set, signalling the
    caller to use the direct structured invoke path instead.
    """
    from maivn._internal.utils.reporting.terminal_reporter import (
        event_router,
    )

    base_reporter = current_reporter.get()
    if base_reporter is None:
        return _ROUTER_SKIPPED

    event_router_reporter_cls = getattr(event_router, "EventRouterReporter", None)
    if not callable(event_router_reporter_cls):
        raise RuntimeError(
            f"EventRouterReporter unavailable for legacy structured output "
            f"(session={session.session_id})"
        )
    routed_reporter = event_router_reporter_cls(
        base_reporter,
        include=STUDIO_EVENT_CATEGORIES,
    )
    routed_token = current_reporter.set(cast("BaseReporter", routed_reporter))
    try:
        return _invoke_structured_invocable(session, structured_invocable, invoke_kwargs)
    finally:
        current_reporter.reset(routed_token)


def _invoke_stream(
    *,
    session: StudioSession,
    executor: Executor,
    loaded: LoadedApp,
    event_invocable: object,
    reporter: StudioReporter | None,
    bridge: EventBridge | None,
    loop: asyncio.AbstractEventLoop,
    manager: ExecutionManagerLike,
    invoke_kwargs: dict[str, Any],
) -> object:
    stream_fn = getattr(event_invocable, "stream", None)
    if not callable(stream_fn):
        raise RuntimeError(f"Executor does not support stream() (session={session.session_id})")
    stream_result = _call_with_delivery_mode("stream", stream_fn, **invoke_kwargs)
    if not isinstance(stream_result, Iterable):
        raise RuntimeError(
            f"SDK stream() returned a non-iterable result (session={session.session_id})"
        )
    raw_events = cast("Iterable[RawSSEEvent]", stream_result)

    normalized_stream_state = NormalizedStreamState()
    forwarding_state = NormalizedEventForwardingState()
    tool_name_map, tool_metadata_map = build_stream_tool_contract_maps(manager, executor)
    final_payload: dict[str, Any] | None = None
    for event in raw_events:
        normalized_events = normalize_stream_event(
            event,
            state=normalized_stream_state,
            default_agent_name=executor.name if loaded.executor_type == "agent" else None,
            default_swarm_name=executor.name if loaded.executor_type == "swarm" else None,
            tool_name_map=tool_name_map,
            tool_metadata_map=tool_metadata_map,
        )
        if reporter is not None:
            replay_normalized_events(
                normalized_events,
                reporter=reporter,
                bridge=bridge,
                loop=loop,
                forwarding_state=forwarding_state,
            )

        payload = _extract_final_payload(event)
        if payload is not None:
            final_payload = payload

    if final_payload is None:
        raise RuntimeError(
            f"SDK stream completed without a final payload event (session={session.session_id})"
        )
    return SDKSessionResponse.model_validate(final_payload)


def _extract_final_payload(event: RawSSEEvent) -> dict[str, Any] | None:
    payload = event.payload
    if isinstance(payload, dict) and (
        event.name == FINAL_EVENT_NAME or payload.get("event_name") == "final"
    ):
        return cast("dict[str, Any]", payload)
    return None


# MARK: Failure Handling


async def _emit_failure_events(
    manager: ExecutionManagerLike,
    session: StudioSession,
    exc: Exception,
    logger: LoggerLike,
) -> None:
    session.status = SessionStatus.FAILED
    session.error = str(exc)
    session.completed_at = datetime.now()

    batch_config = session.metadata.get("batch_config")
    if isinstance(batch_config, dict):
        await _emit_batch_failure_event(manager, session, cast("dict[str, Any]", batch_config), exc)

    await manager.emit_event(
        session,
        "error",
        {
            "session_id": session.session_id,
            "error": str(exc),
        },
    )

    logger.exception("Session %s failed", session.session_id)


async def _emit_batch_failure_event(
    manager: ExecutionManagerLike,
    session: StudioSession,
    batch_config: dict[str, Any],
    exc: Exception,
) -> None:
    failed_items = _build_failed_batch_items(batch_config, exc)
    turn_count = len([m for m in session.messages if isinstance(m, HumanMessage)])
    batch_id = f"{session.session_id}:turn:{turn_count}"
    await manager.emit_event(
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


def _build_failed_batch_items(
    batch_config: dict[str, Any],
    exc: Exception,
) -> list[dict[str, Any]]:
    raw_rows = batch_config.get("rows")
    failed_items: list[dict[str, Any]] = []
    if isinstance(raw_rows, list):
        for index, row in enumerate(cast("list[object]", raw_rows)):
            if not isinstance(row, dict):
                continue
            typed_row = cast("dict[str, Any]", row)
            input_text = str(typed_row.get("message", "")).strip()
            if not input_text:
                continue
            failed_items.append(
                {
                    "index": index,
                    "label": typed_row.get("label"),
                    "input": input_text,
                    "variant": typed_row.get("variant"),
                    "model": typed_row.get("model"),
                    "reasoning": typed_row.get("reasoning"),
                    "status": "failed",
                    "error": str(exc),
                    "responses": [],
                    "response": "",
                    "result": None,
                    "token_usage": None,
                }
            )

    if failed_items:
        return failed_items

    raw_messages = batch_config.get("messages")
    if not isinstance(raw_messages, list):
        return failed_items
    return [
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
            for item in cast("list[object]", raw_messages)
            if isinstance(item, str) and item.strip()
        )
    ]


__all__ = ["execute_session"]
