"""Tool / agent / hook reporting — forwards SDK callbacks onto the EventBridge."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("maivn_studio.services.studio_reporter.reporter")


# MARK: Tool Reporting Mixin


class ToolReportingMixin:
    """Bridge-forwarding implementation of the tool/agent/hook reporter surface."""

    # Attributes provided by :class:`StudioReporter` (declared here so pyright
    # can typecheck the mixin in isolation).
    _bridge: Any
    _submit: Any
    _tool_types: dict[str, tuple[str, str, str | None, str | None]]
    _stream_text_by_tool_id: dict[str, str]
    _current_tool_name: str | None

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

    def report_hook_fired(
        self,
        *,
        name: str,
        stage: str,
        status: str,
        target_type: str,
        target_id: str | None = None,
        target_name: str | None = None,
        source: str | None = None,
        error: str | None = None,
        elapsed_ms: int | None = None,
    ) -> None:
        """Forward a developer-registered hook firing onto the EventBridge.

        Studio's frontend listens for ``hook_fired`` events and renders the
        hook name + status as a persistent header (``stage == "before"``)
        or footer (``stage == "after"``) on the matching tool card or
        scope card. ``source`` tells the UI which level (``"tool"`` /
        ``"scope"`` / ``"swarm"``) defined the hook so the pill label
        stays unambiguous when multiple sources fire on the same target.
        """
        self._submit(
            self._bridge.emit_hook_fired(
                name=name,
                stage=stage,
                status=status,
                target_type=target_type,
                target_id=target_id,
                target_name=target_name,
                source=source,
                error=error,
                elapsed_ms=elapsed_ms,
            )
        )


__all__ = ["ToolReportingMixin"]
