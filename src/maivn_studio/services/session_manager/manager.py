"""Session manager class and global accessor."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import BaseMessage

from maivn_studio.config.models import AppConfig

from .events import emit_event, emit_session_start_event
from .execution import execute_session, flush_reporter_events, supports_structured_output_kwarg
from .lifecycle import (
    cancel_session_record,
    create_session_record,
    end_session_record,
    release_loaded_app,
    send_followup_message,
    shutdown_sessions,
    start_session_execution,
    submit_interrupt_response,
)
from .messages import (
    apply_turn_configuration,
    consume_queued_messages,
    create_message,
    enqueue_message,
    resolve_structured_output_metadata_fallback,
)
from .models import (
    StudioSession,
)

logger = logging.getLogger(__name__)


# MARK: Session Manager


class SessionManager:
    """Manages app execution sessions."""

    def __init__(self) -> None:
        self._sessions: dict[str, StudioSession] = {}
        self._by_thread: dict[str, list[str]] = {}

    async def shutdown(self) -> None:
        sessions = list(self._sessions.values())
        await shutdown_sessions(sessions)
        self._sessions.clear()
        self._by_thread.clear()

    @property
    def sessions(self) -> list[StudioSession]:
        """Get all sessions."""
        return list(self._sessions.values())

    def get(self, session_id: str) -> StudioSession | None:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_by_thread(self, thread_id: str) -> list[StudioSession]:
        """Get all sessions for a thread."""
        session_ids = self._by_thread.get(thread_id, [])
        return [self._sessions[sid] for sid in session_ids if sid in self._sessions]

    @staticmethod
    def _apply_turn_configuration(
        session: StudioSession,
        *,
        structured_output: dict[str, Any] | None,
        invocation_kwargs: dict[str, Any] | None,
        batch_config: dict[str, Any] | None = None,
    ) -> None:
        apply_turn_configuration(
            session,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
        )

    @staticmethod
    def _resolve_structured_output_metadata_fallback(
        *,
        loaded_app: Any,
        structured_output_model: type[Any] | None,
        user_invoke_kwargs: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        return resolve_structured_output_metadata_fallback(
            loaded_app=loaded_app,
            structured_output_model=structured_output_model,
            user_invoke_kwargs=user_invoke_kwargs,
        )

    @staticmethod
    def _build_tool_contract_maps(
        executor: Any,
    ) -> tuple[dict[str, str], dict[str, dict[str, Any]]]:
        """Build canonical contract maps for swarm agent invocation tools.

        The SDK generates UUID-based tool IDs for agent invocation tools via
        ``create_uuid(f'agent_invoke_{agent_id}')``. This helper mirrors that
        behavior so Studio can resolve canonical agent invocation metadata when
        processing normalized contract stream events.
        """
        # The executor may be a Swarm directly or an Agent with a parent swarm.
        from maivn._internal.api.swarm.swarm import Swarm
        from maivn_shared import create_uuid

        if isinstance(executor, Swarm):
            swarm = executor
        else:
            get_swarm = getattr(executor, "get_swarm", None)
            swarm = get_swarm() if callable(get_swarm) else None
        if swarm is None:
            return {}, {}

        name_map: dict[str, str] = {}
        metadata_map: dict[str, dict[str, Any]] = {}
        swarm_name = getattr(swarm, "name", None)

        for agent in getattr(swarm, "agents", []):
            agent_id = getattr(agent, "id", None)
            agent_name = getattr(agent, "name", None)
            if not isinstance(agent_id, str) or not agent_id.strip():
                continue
            if not isinstance(agent_name, str) or not agent_name.strip():
                continue

            normalized_agent_id = agent_id.strip()
            normalized_agent_name = agent_name.strip()
            tool_uuid = str(create_uuid(f"agent_invoke_{normalized_agent_id}"))
            name_map[tool_uuid] = normalized_agent_name
            metadata_map[tool_uuid] = {
                "tool_name": normalized_agent_name,
                "tool_type": "agent",
                "target_agent_id": normalized_agent_id,
                "agent_name": normalized_agent_name,
                "swarm_name": swarm_name,
            }

        return name_map, metadata_map

    @staticmethod
    def _enqueue_message(
        session: StudioSession,
        *,
        message: str,
        message_type: str,
        attachments: list[dict[str, Any]] | None,
        structured_output: dict[str, Any] | None,
        invocation_kwargs: dict[str, Any] | None,
        batch_config: dict[str, Any] | None,
    ) -> None:
        enqueue_message(
            session,
            message=message,
            message_type=message_type,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
        )

    def _consume_queued_messages(self, session: StudioSession) -> int:
        count, next_structured_output, next_invocation_kwargs, next_batch_config = (
            consume_queued_messages(
                session,
                create_message_fn=self._create_message,
            )
        )
        self._apply_turn_configuration(
            session,
            structured_output=next_structured_output,
            invocation_kwargs=next_invocation_kwargs,
            batch_config=next_batch_config,
        )
        return count

    async def _emit_session_start_event(
        self,
        session: StudioSession,
        *,
        executor: Any,
        executor_type: str,
        consumed_queued_message_count: int = 0,
    ) -> None:
        await emit_session_start_event(
            self,
            session,
            executor=executor,
            executor_type=executor_type,
            consumed_queued_message_count=consumed_queued_message_count,
        )

    # MARK: Session Lifecycle

    async def create_session(
        self,
        app_config: AppConfig,
        variant: str | None = None,
        thread_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        private_data: dict[str, Any] | None = None,
    ) -> StudioSession:
        """Create a new execution session.

        Args:
            app_config: App configuration to execute.
            variant: Optional variant name.
            thread_id: Optional thread ID for conversation continuity.
            metadata: Optional session metadata.
            private_data: Optional user-provided private data values.

        Returns:
            Created StudioSession.
        """
        session = await create_session_record(
            sessions=self._sessions,
            sessions_by_thread=self._by_thread,
            app_config=app_config,
            variant=variant,
            thread_id=thread_id,
            metadata=metadata,
            private_data=private_data,
        )
        logger.info("Created session %s for app %s", session.session_id, app_config.id)
        return session

    async def start_session(
        self,
        session: StudioSession,
        message: str,
        message_type: str = "human",
        system_message: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
        structured_output: dict[str, Any] | None = None,
        invocation_kwargs: dict[str, Any] | None = None,
        batch_config: dict[str, Any] | None = None,
    ) -> None:
        """Start executing a session with an initial message.

        Args:
            session: The session to start.
            message: Initial user message.
            message_type: Message type (human, redacted).
            system_message: Optional system message prepended to conversation.
            attachments: Optional message attachments for multimodal ingestion.
            structured_output: Optional structured output configuration.
            invocation_kwargs: Optional SDK invocation parameters (model, reasoning, etc.).
            batch_config: Optional batch execution parameters for this turn.
        """
        await start_session_execution(
            self,
            session,
            message=message,
            message_type=message_type,
            system_message=system_message,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
        )
        logger.info("Started session %s", session.session_id)

    async def send_message(
        self,
        session: StudioSession,
        message: str,
        message_type: str = "human",
        attachments: list[dict[str, Any]] | None = None,
        structured_output: dict[str, Any] | None = None,
        invocation_kwargs: dict[str, Any] | None = None,
        batch_config: dict[str, Any] | None = None,
    ) -> None:
        """Send a follow-up message for multi-turn conversation.

        Args:
            session: The session to send to.
            message: The message content.
            message_type: Message type (human, redacted, system).
            attachments: Optional message attachments for multimodal ingestion.
            structured_output: Optional structured output configuration.
            invocation_kwargs: Optional SDK invocation parameters (model, reasoning, etc.).
            batch_config: Optional batch execution parameters for this turn.
        """
        await send_followup_message(
            self,
            session,
            message=message,
            message_type=message_type,
            attachments=attachments,
            structured_output=structured_output,
            invocation_kwargs=invocation_kwargs,
            batch_config=batch_config,
        )
        logger.info("Continuing session %s with new message", session.session_id)

    async def submit_interrupt(
        self,
        session: StudioSession,
        data_key: str,
        value: Any,
    ) -> None:
        """Submit an interrupt response.

        Args:
            session: The session waiting for input.
            data_key: The data key being responded to.
            value: The response value.
        """
        await submit_interrupt_response(
            session,
            data_key=data_key,
            value=value,
        )

    async def end_session(self, session: StudioSession) -> None:
        """Explicitly end a session (mark as completed).

        Used when the user wants to end the conversation.

        Args:
            session: The session to end.
        """
        await end_session_record(self, session)
        logger.info("Ended session %s", session.session_id)

    async def cancel_session(self, session: StudioSession) -> None:
        """Cancel a running session.

        Args:
            session: The session to cancel.
        """
        await cancel_session_record(session)
        logger.info("Cancelled session %s", session.session_id)

    # MARK: Execution

    async def _execute_session(self, session: StudioSession) -> None:
        await execute_session(self, session, logger)

    @staticmethod
    def _supports_structured_output_kwarg(executor: Any) -> bool:
        return supports_structured_output_kwarg(executor)

    @staticmethod
    async def _flush_reporter_events(reporter: Any | None) -> None:
        await flush_reporter_events(reporter, logger)

    # MARK: Event Helpers

    async def _emit_event(
        self,
        session: StudioSession,
        event_type: str,
        data: dict[str, Any],
    ) -> None:
        """Emit an event to the session's event bridge for SSE streaming.

        Args:
            session: The session to emit to.
            event_type: Type of event.
            data: Event data.
        """
        await emit_event(session, event_type, data, logger=logger)

    def _create_message(
        self,
        content: str,
        message_type: str,
        *,
        attachments: list[dict[str, Any]] | None = None,
    ) -> BaseMessage:
        """Create a message of the appropriate type.

        Args:
            content: Message content.
            message_type: Type (human, redacted, system).
            attachments: Optional attachment payloads for human/redacted messages.

        Returns:
            LangChain message instance.
        """
        return create_message(
            content,
            message_type,
            attachments=attachments,
        )

    def _release_loaded_app(self, session: StudioSession) -> None:
        release_loaded_app(session)


# MARK: Global Manager

_manager: SessionManager | None = None


def get_session_manager() -> SessionManager:
    """Get the global session manager instance."""
    global _manager
    if _manager is None:
        _manager = SessionManager()
    return _manager
