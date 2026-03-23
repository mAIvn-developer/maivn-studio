"""Execution helpers for session management."""

from __future__ import annotations

import asyncio
import contextvars
import inspect
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage
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

            result = await asyncio.to_thread(ctx.run, _invoke_executor)
            await flush_reporter_events(reporter, logger)

            session.result = result

            response = _latest_response_text(getattr(result, "responses", None))
            if response is None:
                response = ""
            session.messages.append(AIMessage(content=response))

            structured_result = None
            if hasattr(result, "result") and result.result is not None:
                from pydantic import BaseModel

                if isinstance(result.result, BaseModel):
                    structured_result = result.result.model_dump()
                elif isinstance(result.result, dict):
                    structured_result = result.result
                else:
                    structured_result = result.result

            turn_duration_ms = int((time_module.time() - turn_start_time) * 1000)

            token_usage = None
            if hasattr(result, "token_usage") and result.token_usage is not None:
                token_usage = {
                    "total_tokens": result.token_usage.total_tokens,
                    "input_tokens": result.token_usage.input_tokens,
                    "output_tokens": result.token_usage.output_tokens,
                    "cache_read_tokens": result.token_usage.cache_read_tokens,
                    "cache_creation_tokens": result.token_usage.cache_creation_tokens,
                    "reasoning_tokens": getattr(result.token_usage, "reasoning_tokens", 0),
                }

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
