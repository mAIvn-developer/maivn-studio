"""Phase / enrichment / status / response reporting.

Bundles every reporter callback that surfaces lifecycle progress or
assistant text onto the bridge — phase chips, system-tool progress, status
messages, and the assistant response chunk fan-out (with contract-stream
suppression when the replay loop is delivering chunks itself).
"""

from __future__ import annotations

from typing import Any

from .streaming import compute_stream_delta, is_contract_stream_mode

# MARK: Phase Reporting Mixin


class PhaseReportingMixin:
    """Reporter callbacks that surface progress / response text to the UI."""

    # Attributes provided by :class:`StudioReporter` (declared here so pyright
    # can typecheck the mixin in isolation).
    _bridge: Any
    _submit: Any
    _response_stream_text_by_assistant_id: dict[str, str]
    _stream_text_by_tool_id: dict[str, str]

    # MARK: - Final response (invoke-mode entry point)

    def print_final_response(self, response: str) -> None:
        # Contract stream mode replays normalized chunks after the SDK stream
        # finishes. Forwarding the final response here would seed the reporter's
        # delta state with the full answer and collapse the replay into one UI
        # chunk.
        if is_contract_stream_mode():
            return
        # Invoke-mode flows never call ``report_response_chunk`` — the SDK only
        # delivers the full response string here. Without forwarding it the UI
        # sees enrichment chips but no actual response text. The delta check
        # still suppresses duplicate invoke-mode callbacks.
        if not isinstance(response, str) or not response:
            return
        source_id = "assistant"
        previous = self._response_stream_text_by_assistant_id.get(source_id, "")
        delta = compute_stream_delta(previous, response)
        if not delta:
            return
        self._response_stream_text_by_assistant_id[source_id] = response
        self._submit(
            self._bridge.emit_assistant_chunk(
                assistant_id=source_id,
                text=delta,
            )
        )

    # MARK: - Session lifecycle

    def report_session_start(self, session_id: str, assistant_id: str) -> None:
        _ = (session_id, assistant_id)
        return

    def report_private_data(self, private_data: dict[str, Any]) -> None:
        _ = private_data
        return

    # MARK: - Phase chips

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

    # MARK: - Enrichment

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

    # MARK: - System tool progress

    def report_system_tool_progress(
        self,
        event_id: str,
        tool_name: str,
        chunk_count: int,
        elapsed_seconds: float,
        text: str | None = None,
    ) -> None:
        if is_contract_stream_mode():
            return

        _ = (tool_name, chunk_count, elapsed_seconds)
        incoming = str(text or "")
        previous = self._stream_text_by_tool_id.get(event_id, "")
        delta = compute_stream_delta(previous, incoming)

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

    # MARK: - Status / response

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
        """Forward streamed assistant text chunks to Studio UI.

        When the caller supplies both ``text`` (delta) and ``full_text``
        (cumulative) and the two are consistent — i.e. ``full_text`` is
        exactly ``previous + text`` — we trust the delta and skip the
        ``O(len(previous))`` divergence scan. Long streaming turns spend
        most chunks on that fast path; the slow path remains as a safety
        net for callers whose snapshots actually diverged.
        """
        if is_contract_stream_mode():
            return

        normalized_assistant_id = assistant_id.strip() if isinstance(assistant_id, str) else ""
        source_id = normalized_assistant_id or "assistant"

        previous = self._response_stream_text_by_assistant_id.get(source_id, "")
        if isinstance(full_text, str):
            if text and len(full_text) == len(previous) + len(text) and full_text.endswith(text):
                # Fast path — caller's snapshot agrees with previous + text.
                delta = text
            else:
                # Slow path — snapshot diverged (or no delta supplied); reconcile.
                delta = compute_stream_delta(previous, full_text)
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


__all__ = ["PhaseReportingMixin"]
