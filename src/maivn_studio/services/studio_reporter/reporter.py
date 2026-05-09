"""Studio reporter that forwards SDK events to the UI event bridge."""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Coroutine, Iterator
from concurrent.futures import Future
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from maivn._internal.utils.reporting.context import current_sdk_delivery_mode
from maivn._internal.utils.reporting.terminal_reporter import BaseReporter

from ..event_bridge import EventBridge
from .interrupts import cleanup_interrupt, get_interrupt_response, register_interrupt

logger = logging.getLogger(__name__)

_normalized_stream_replay_active: ContextVar[bool] = ContextVar(
    "studio_normalized_stream_replay_active",
    default=False,
)


@contextmanager
def normalized_stream_replay_context() -> Iterator[None]:
    """Allow normalized replay chunks through contract-stream suppression."""
    token = _normalized_stream_replay_active.set(True)
    try:
        yield
    finally:
        _normalized_stream_replay_active.reset(token)


# MARK: Reporter


class StudioReporter(BaseReporter):
    """Lightweight reporter that pushes SDK callbacks into the Studio bridge.

    Replay ownership and bridge-level identity handling live upstream in the
    session execution path and shared ``maivn.events.EventBridge`` contract.
    This reporter stays intentionally thin and forwards only the SDK callbacks
    raised during the active turn.
    """

    def __init__(self, bridge: EventBridge, loop: asyncio.AbstractEventLoop) -> None:
        self._bridge = bridge
        self._loop = loop
        # Maps tool_id -> (tool_type, tool_name, agent_name, swarm_name)
        self._tool_types: dict[str, tuple[str, str, str | None, str | None]] = {}
        # Tracks full streaming text per system tool to emit deltas to the UI.
        self._stream_text_by_tool_id: dict[str, str] = {}
        # Tracks streamed assistant text by source to emit stable deltas.
        self._response_stream_text_by_assistant_id: dict[str, str] = {}
        # Track current tool context for interrupts
        self._current_tool_name: str | None = None
        self._interrupt_counter = 0
        # Unique suffix per reporter instance so interrupt IDs don't collide
        # across turns (each turn creates a fresh StudioReporter).
        self._turn_id = uuid.uuid4().hex[:8]
        # Track bridge submissions so callers can wait for UI events to land
        # before emitting terminal turn/session events.
        self._pending_submissions: set[Future[Any]] = set()
        self._pending_submissions_lock = threading.Lock()

    @property
    def session_id(self) -> str:
        """Get session ID from bridge."""
        return self._bridge.session_id

    # MARK: - Output

    def print_header(self, title: str, subtitle: str = "") -> None:
        _ = (title, subtitle)
        return

    def print_section(self, title: str, style: str = "bold cyan") -> None:
        _ = (title, style)
        return

    def print_event(
        self,
        event_type: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        _ = (event_type, message, details)
        return

    def print_summary(self, token_usage: Any | None = None) -> None:
        _ = token_usage
        return

    def print_final_result(self, result: Any) -> None:
        _ = result
        return

    def print_final_response(self, response: str) -> None:
        # Contract stream mode replays normalized chunks after the SDK stream
        # finishes. Forwarding the final response here would seed the reporter's
        # delta state with the full answer and collapse the replay into one UI
        # chunk.
        if self._is_contract_stream_mode():
            return
        # Invoke-mode flows never call ``report_response_chunk`` — the SDK only
        # delivers the full response string here. Without forwarding it the UI
        # sees enrichment chips but no actual response text. The delta check
        # still suppresses duplicate invoke-mode callbacks.
        if not isinstance(response, str) or not response:
            return
        source_id = "assistant"
        previous = self._response_stream_text_by_assistant_id.get(source_id, "")
        delta = self._compute_stream_delta(previous, response)
        if not delta:
            return
        self._response_stream_text_by_assistant_id[source_id] = response
        self._submit(
            self._bridge.emit_assistant_chunk(
                assistant_id=source_id,
                text=delta,
            )
        )

    def print_error_summary(self, error: str) -> None:
        _ = error
        return

    # MARK: - Progress

    @contextmanager
    def live_progress(self, description: str = "Processing...") -> Iterator[Any]:
        _ = description
        yield None

    def update_progress(self, task_id: Any, description: str | None = None) -> None:
        _ = (task_id, description)
        return

    # MARK: - Input

    @contextmanager
    def prepare_for_user_input(self) -> Iterator[None]:
        yield

    def get_input(
        self,
        prompt: str,
        *,
        input_type: str = "text",
        choices: list[str] | None = None,
        data_key: str | None = None,
        arg_name: str | None = None,
    ) -> str:
        """Collect input via UI instead of terminal.

        Emits an interrupt_required SSE event and waits for the response
        to be provided via the resolve_interrupt API.

        Args:
            prompt: The prompt to display to the user.
            input_type: Type of input (text, choice, boolean, number, email, password).
            choices: Available choices for choice/literal input types.
            data_key: Optional data key for interrupt storage.
            arg_name: Optional argument name in the tool signature.

        Returns:
            The user's input string.
        """
        # Generate unique interrupt ID (includes turn_id to avoid collisions across turns)
        self._interrupt_counter += 1
        interrupt_id = f"{self.session_id}-interrupt-{self._turn_id}-{self._interrupt_counter}"

        logger.info(
            f'[STUDIO_REPORTER] get_input called: prompt="{prompt[:50]}...", '
            f"interrupt_id={interrupt_id}, input_type={input_type}, choices={choices}"
        )

        resolved_data_key = data_key or arg_name or interrupt_id
        interrupt_aliases = [f"{self.session_id}:{resolved_data_key}"]
        if arg_name and arg_name != resolved_data_key:
            interrupt_aliases.append(f"{self.session_id}:{arg_name}")

        # Register the interrupt and get the event to wait on
        wait_event = register_interrupt(interrupt_id, aliases=interrupt_aliases)

        # Always emit the interrupt event from the reporter — the reporter
        # owns the interrupt_id that the resolve API uses.  The contract
        # stream normalizer skips interrupt_required events to avoid
        # duplicate cards with mismatched IDs.
        self._submit(
            self._bridge.emit_interrupt_required(
                interrupt_id=interrupt_id,
                data_key=resolved_data_key,
                prompt=prompt.strip(),
                arg_name=arg_name,
                tool_name=self._current_tool_name,
                input_type=input_type,
                choices=choices,
            )
        )

        logger.info(f"[STUDIO_REPORTER] Waiting for interrupt response: {interrupt_id}")

        # Wait for the response (blocks until resolve_interrupt is called).
        # Interrupts are designed for long waits (up to 7 days) — the server
        # checkpoints them so they don't hold up resources.
        if not wait_event.wait(timeout=604800):
            logger.warning(f"[STUDIO_REPORTER] Interrupt {interrupt_id} timed out")
            cleanup_interrupt(interrupt_id)
            return ""

        # Get the response
        response = get_interrupt_response(interrupt_id)
        cleanup_interrupt(interrupt_id)

        logger.info(
            f"[STUDIO_REPORTER] Received interrupt response: {interrupt_id} -> "
            f'"{response[:50] if response else "(empty)"}"'
        )

        return response or ""

    # MARK: - Session Reporting

    def report_session_start(self, session_id: str, assistant_id: str) -> None:
        _ = (session_id, assistant_id)
        return

    def report_private_data(self, private_data: dict[str, Any]) -> None:
        _ = private_data
        return

    def report_phase_change(self, phase: str) -> None:
        normalized_phase = phase.strip()
        if not normalized_phase:
            return

        phase_messages = {
            "planning": "Planning actions...",
            "planning_assignments": "Planning assignments...",
            "executing_actions": "Executing actions...",
            "executing_assignments": "Executing assignments...",
            "synthesizing": "Synthesizing response...",
        }
        message = phase_messages.get(
            normalized_phase,
            f"{normalized_phase.replace('_', ' ').capitalize()}...",
        )
        self._submit(
            self._bridge.emit_enrichment(
                phase=normalized_phase,
                message=message,
            )
        )

    # MARK: - Tool Reporting

    def report_tool_start(
        self,
        tool_name: str,
        event_id: str,
        tool_type: str | None = None,
        agent_name: str | None = None,
        tool_args: dict[str, Any] | None = None,
        swarm_name: str | None = None,
    ) -> None:
        tool_id = str(event_id)

        logger.info(
            f"[STUDIO_REPORTER] report_tool_start: tool={tool_name}, "
            f"type={tool_type}, agent={agent_name}, swarm={swarm_name}"
        )
        resolved_type = (tool_type or "func").lower()
        self._tool_types[tool_id] = (resolved_type, tool_name, agent_name, swarm_name)

        # Track current tool name for interrupt context
        self._current_tool_name = tool_name

        if resolved_type == "system":
            self._stream_text_by_tool_id[tool_id] = ""
            self._submit(
                self._bridge.emit_system_tool_start(
                    tool_type=tool_name,
                    tool_id=tool_id,
                    params=tool_args,
                    agent_name=agent_name,
                    swarm_name=swarm_name,
                )
            )
            return

        self._submit(
            self._bridge.emit_tool_event(
                tool_name=tool_name,
                tool_id=tool_id,
                status="executing",
                args=tool_args,
                agent_name=agent_name,
                swarm_name=swarm_name,
                tool_type=resolved_type,
            )
        )

    def report_tool_complete(
        self,
        event_id: str,
        elapsed_ms: int | None = None,
        result: Any | None = None,
    ) -> None:
        _ = elapsed_ms
        tool_id = str(event_id)
        tool_info = self._tool_types.pop(tool_id, ("", tool_id, None, None))
        tool_type, tool_name = tool_info[0], tool_info[1]
        agent_name = tool_info[2] if len(tool_info) > 2 else None
        swarm_name = tool_info[3] if len(tool_info) > 3 else None

        if tool_type == "system":
            self._stream_text_by_tool_id.pop(tool_id, None)
            self._submit(self._bridge.emit_system_tool_complete(tool_id=tool_id, result=result))
            return

        self._submit(
            self._bridge.emit_tool_event(
                tool_name=tool_name,
                tool_id=tool_id,
                status="completed",
                result=result,
                agent_name=agent_name,
                swarm_name=swarm_name,
                tool_type=tool_type,
            )
        )

    def report_tool_error(
        self,
        tool_name: str,
        error: str,
        event_id: str | None = None,
        elapsed_ms: int | None = None,
    ) -> None:
        _ = elapsed_ms
        tool_id = str(event_id or tool_name)
        self._stream_text_by_tool_id.pop(tool_id, None)
        self._submit(
            self._bridge.emit_tool_event(
                tool_name=tool_name,
                tool_id=tool_id,
                status="failed",
                error=error,
            )
        )

    def report_model_tool_complete(
        self,
        tool_name: str,
        event_id: str | None = None,
        agent_name: str | None = None,
        swarm_name: str | None = None,
        result: Any | None = None,
    ) -> None:
        tool_id = str(event_id or tool_name)
        self._submit(
            self._bridge.emit_tool_event(
                tool_name=tool_name,
                tool_id=tool_id,
                status="completed",
                result=result,
                agent_name=agent_name,
                swarm_name=swarm_name,
                tool_type="model",
            )
        )

    def report_agent_assignment(
        self,
        *,
        agent_name: str,
        status: str,
        assignment_id: str | None = None,
        swarm_name: str | None = None,
        error: str | None = None,
        result: Any | None = None,
    ) -> None:
        self._submit(
            self._bridge.emit_agent_assignment(
                agent_name=agent_name,
                status=status,
                assignment_id=assignment_id,
                swarm_name=swarm_name,
                error=error,
                result=result,
            )
        )

    def report_enrichment(
        self,
        *,
        phase: str,
        message: str,
        scope_id: str | None = None,
        scope_name: str | None = None,
        scope_type: str | None = None,
        memory: dict[str, Any] | None = None,
        redaction: dict[str, Any] | None = None,
    ) -> None:
        normalized_scope_type = None
        if isinstance(scope_type, str) and scope_type.strip():
            candidate = scope_type.strip().lower()
            if candidate in {"agent", "swarm"}:
                normalized_scope_type = candidate

        normalized_scope_id = (
            scope_id.strip() if isinstance(scope_id, str) and scope_id.strip() else None
        )
        normalized_scope_name = (
            scope_name.strip() if isinstance(scope_name, str) and scope_name.strip() else None
        )

        self._submit(
            self._bridge.emit_enrichment(
                phase=phase,
                message=message,
                scope_id=normalized_scope_id,
                scope_name=normalized_scope_name,
                scope_type=normalized_scope_type,
                memory=dict(memory) if isinstance(memory, dict) and memory else None,
                redaction=dict(redaction) if isinstance(redaction, dict) and redaction else None,
            )
        )

    def report_system_tool_progress(
        self,
        event_id: str,
        tool_name: str,
        chunk_count: int,
        elapsed_seconds: float,
        text: str | None = None,
    ) -> None:
        if self._is_contract_stream_mode():
            return

        _ = (tool_name, chunk_count, elapsed_seconds)
        incoming = str(text or "")
        previous = self._stream_text_by_tool_id.get(event_id, "")
        delta = self._compute_stream_delta(previous, incoming)

        self._stream_text_by_tool_id[event_id] = incoming
        if not delta:
            return

        self._submit(
            self._bridge.emit_system_tool_chunk(
                tool_id=event_id,
                text=delta,
                progress=None,
            )
        )

    def report_status_message(
        self,
        message: str,
        *,
        assistant_id: str | None = None,
    ) -> None:
        """Forward a standalone status message to Studio UI."""
        source_id = (
            assistant_id.strip()
            if isinstance(assistant_id, str) and assistant_id.strip()
            else "assistant"
        )
        self._submit(
            self._bridge.emit_status_message(
                assistant_id=source_id,
                message=message,
            )
        )

    def report_response_chunk(
        self,
        text: str,
        *,
        assistant_id: str | None = None,
        full_text: str | None = None,
    ) -> None:
        """Forward streamed assistant text chunks to Studio UI."""
        if self._is_contract_stream_mode():
            return

        normalized_assistant_id = assistant_id.strip() if isinstance(assistant_id, str) else ""
        source_id = normalized_assistant_id or "assistant"

        previous = self._response_stream_text_by_assistant_id.get(source_id, "")
        if isinstance(full_text, str):
            delta = self._compute_stream_delta(previous, full_text)
            self._response_stream_text_by_assistant_id[source_id] = full_text
        else:
            delta = str(text or "")
            self._response_stream_text_by_assistant_id[source_id] = previous + delta

        if not delta:
            return

        self._submit(
            self._bridge.emit_assistant_chunk(
                assistant_id=source_id,
                text=delta,
            )
        )

    @staticmethod
    def _compute_stream_delta(previous: str, incoming: str) -> str:
        """Compute append-only deltas from cumulative snapshots."""
        if not incoming:
            return ""
        if not previous:
            return incoming
        if incoming.startswith(previous):
            return incoming[len(previous) :]
        if previous.startswith(incoming):
            return ""

        max_len = min(len(previous), len(incoming))
        shared = 0
        while shared < max_len and previous[shared] == incoming[shared]:
            shared += 1
        if shared == 0:
            return incoming
        return incoming[shared:]

    @staticmethod
    def _is_contract_stream_mode() -> bool:
        return current_sdk_delivery_mode.get() == "stream" and not (
            _normalized_stream_replay_active.get()
        )

    # MARK: - Helpers

    async def flush(self) -> None:
        """Wait for in-flight bridge submissions to finish.

        Studio dispatches reporter events from worker threads via
        ``run_coroutine_threadsafe``. Without draining those futures before
        emitting ``turn_complete`` / ``error``, terminal events can overtake
        tool and agent events on the bridge.
        """
        if self._loop.is_closed():
            return

        while True:
            with self._pending_submissions_lock:
                pending = tuple(self._pending_submissions)

            if not pending:
                return

            results = await asyncio.gather(
                *(asyncio.wrap_future(future) for future in pending),
                return_exceptions=True,
            )
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(
                        "[STUDIO_REPORTER] Bridge submission failed during flush: %s",
                        result,
                    )

    def _submit(self, coro: Coroutine[Any, Any, Any]) -> None:
        if self._loop.is_closed():
            logger.warning("[STUDIO_REPORTER] Event loop is closed, cannot submit event")
            coro.close()
            return
        logger.debug("[STUDIO_REPORTER] Submitting event to bridge")
        try:
            future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        except RuntimeError as exc:
            coro.close()
            logger.warning("[STUDIO_REPORTER] Bridge submission failed: %s", exc)
            return

        with self._pending_submissions_lock:
            self._pending_submissions.add(future)

        def _cleanup_submission(done_future: Future[Any]) -> None:
            with self._pending_submissions_lock:
                self._pending_submissions.discard(done_future)

            try:
                done_future.result()
            except Exception as exc:
                logger.warning("[STUDIO_REPORTER] Bridge submission failed: %s", exc)

        future.add_done_callback(_cleanup_submission)
