# pyright: strict
"""Phase / enrichment / status / response reporting.

Bundles every reporter callback that surfaces lifecycle progress or
assistant text onto the bridge — phase chips, system-tool progress, status
messages, and the assistant response chunk fan-out (with contract-stream
suppression when the replay loop is delivering chunks itself).
"""

from __future__ import annotations

from abc import ABC

from .state import ReporterState
from .streaming import compute_stream_delta, is_contract_stream_mode

# MARK: Phase Reporting Mixin


class PhaseReportingMixin(ReporterState, ABC):
    """Reporter callbacks that surface progress / response text to the UI.

    These methods override :class:`BaseReporter` callbacks only once composed
    into :class:`StudioReporter`; the mixin does not inherit ``BaseReporter``,
    so ``@override`` is omitted on these methods.
    """

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
        if not response:
            return
        source_id = "assistant"
        previous = self.response_stream_text_by_assistant_id.get(source_id, "")
        delta = compute_stream_delta(previous, response)
        if not delta:
            return
        self.response_stream_text_by_assistant_id[source_id] = response
        self._submit(
            self._bridge.emit_assistant_chunk(
                assistant_id=source_id,
                text=delta,
            )
        )

    # MARK: - Session lifecycle

    def report_session_start(self, session_id: str, assistant_id: str) -> None:
        _ = (session_id, assistant_id)
        # Defensive: clear any stale ``_next_response_chunk_replaces`` flag
        # that may have been set by a prior turn's reevaluate_accrued
        # without being consumed (e.g. synthesis aborted before any chunk
        # arrived). A new session/turn should always start fresh.
        self._next_response_chunk_replaces = False

    def report_private_data(self, private_data: dict[str, object]) -> None:
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
        memory: dict[str, object] | None = None,
        redaction: dict[str, object] | None = None,
        source: str | None = None,
        trigger_tool: str | None = None,
        target_tool: str | None = None,
        reevaluate_count: int | None = None,
        collected_count: int | None = None,
    ) -> None:
        normalized_scope_type = None
        if scope_type and scope_type.strip():
            candidate = scope_type.strip().lower()
            if candidate in {"agent", "swarm"}:
                normalized_scope_type = candidate

        normalized_scope_id = scope_id.strip() if scope_id and scope_id.strip() else None
        normalized_scope_name = scope_name.strip() if scope_name and scope_name.strip() else None

        # Bundle reevaluate attribution into a single sub-dict mirroring the
        # ``memory`` / ``redaction`` shape so the bridge stays uniform. Empty
        # values are dropped so legacy enrichment phases (memory, redaction)
        # don't carry an empty ``reevaluate`` key on the wire.
        reevaluate_payload: dict[str, object] = {}
        if source and source.strip():
            reevaluate_payload["source"] = source.strip()
        if trigger_tool and trigger_tool.strip():
            reevaluate_payload["trigger_tool"] = trigger_tool.strip()
        if target_tool and target_tool.strip():
            reevaluate_payload["target_tool"] = target_tool.strip()
        if reevaluate_count is not None:
            reevaluate_payload["reevaluate_count"] = reevaluate_count
        if collected_count is not None:
            reevaluate_payload["collected_count"] = collected_count

        # Reevaluate restarts synthesis on a fresh server-side thread,
        # often under a NEW ``assistant_id``. Clear the per-assistant /
        # per-tool stream caches so delta computation starts from an empty
        # baseline, and set a one-shot global flag so the NEXT streamed
        # chunk — whatever assistant_id it carries — is emitted with
        # ``replace_content=True``. The UI overwrites the bubble for that
        # chunk; subsequent chunks within the new cycle append normally.
        if phase == "reevaluate_accrued":
            self.response_stream_text_by_assistant_id.clear()
            self.stream_text_by_tool_id.clear()
            self._next_response_chunk_replaces = True

        self._submit(
            self._bridge.emit_enrichment(
                phase=phase,
                message=message,
                scope_id=normalized_scope_id,
                scope_name=normalized_scope_name,
                scope_type=normalized_scope_type,
                memory=dict(memory) if memory else None,
                redaction=dict(redaction) if redaction else None,
                reevaluate=reevaluate_payload or None,
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
        previous = self.stream_text_by_tool_id.get(event_id, "")
        delta = compute_stream_delta(previous, incoming)

        self.stream_text_by_tool_id[event_id] = incoming
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
        source_id = assistant_id.strip() if assistant_id and assistant_id.strip() else "assistant"
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
        replace_content: bool = False,
    ) -> None:
        """Forward streamed assistant text chunks to Studio UI.

        Determines ``replace_content`` FIRST (from caller, one-shot flag,
        or divergence detection) and then computes the emitted chunk text
        based on that. When replacing, we emit the full cumulative text so
        the UI overwrites with complete content; when appending, we emit
        only the suffix-after-shared-prefix so the UI appends cleanly.
        """
        if is_contract_stream_mode():
            return

        source_id = assistant_id.strip() if assistant_id else ""
        source_id = source_id or "assistant"

        previous = self.response_stream_text_by_assistant_id.get(source_id, "")

        # ----- Step 1: decide whether this chunk REPLACES or APPENDS -----
        # ``replace_content`` arrives from three sources, any of which is
        # sufficient to overwrite the UI bubble for this chunk:
        #   1. The caller passes it explicitly (the normalize-forward layer
        #      threads it in from the AppEvent payload — that's how Studio's
        #      stream() path delivers the reevaluate signal here);
        #   2. The one-shot flag set by ``report_enrichment`` when a
        #      ``reevaluate_accrued`` event was just processed (this hits the
        #      invoke() path where enrichments arrive in the same reporter
        #      callback sequence);
        #   3. Divergent-stream detection: prior cumulative text and the new
        #      ``full_text`` share neither side as a prefix (synthesis
        #      restart, intra-cycle retry, or mid-stream revision).
        diverged_stream = False
        if (
            full_text
            and previous
            and (not full_text.startswith(previous) and not previous.startswith(full_text))
        ):
            diverged_stream = True
        flag_was_set = self._next_response_chunk_replaces
        if not replace_content:
            replace_content = flag_was_set or diverged_stream
        if flag_was_set:
            # Consume the one-shot flag unconditionally so it can't bleed
            # into a future turn if a downstream condition skips this chunk.
            self._next_response_chunk_replaces = False

        # ----- Step 2: compute the chunk text to emit -----
        if replace_content and full_text:
            # Overwriting the bubble: emit the full new cumulative text so
            # the UI replaces with complete content (not just the divergent
            # suffix that ``compute_stream_delta`` would return).
            delta = full_text
            self.response_stream_text_by_assistant_id[source_id] = full_text
        elif full_text is not None:
            if text and len(full_text) == len(previous) + len(text) and full_text.endswith(text):
                # Fast path — caller's snapshot agrees with previous + text.
                delta = text
            else:
                # Slow path — reconcile via shared-prefix scan.
                delta = compute_stream_delta(previous, full_text)
            self.response_stream_text_by_assistant_id[source_id] = full_text
        else:
            delta = str(text or "")
            self.response_stream_text_by_assistant_id[source_id] = previous + delta

        if not delta:
            return

        self._submit(
            self._bridge.emit_assistant_chunk(
                assistant_id=source_id,
                text=delta,
                replace_content=replace_content,
            )
        )


__all__ = ["PhaseReportingMixin"]
