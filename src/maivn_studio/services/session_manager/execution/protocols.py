"""Type contracts the execution helpers reach back into the manager through.

The execution turn loop calls back into the owning ``SessionManager`` for
event emission, message creation, queue draining, and tool-contract map
construction. :class:`ExecutionManagerLike` extends the shared
:class:`maivn_studio.services.session_manager.protocols.SessionManagerLike`
with the additional execution-only callbacks, so ``execute_session`` and the
batch driver can stay decoupled from the concrete manager while remaining
fully typed.
"""

# pyright: strict
from __future__ import annotations

from typing import Any, Protocol

from ..models import StudioSession
from ..protocols import Executor, SessionManagerLike

# MARK: Manager Protocol

# Tool-contract map shapes shared across the stream/normalize boundary. The
# metadata value stays ``dict[str, Any]`` so the maps remain assignable to the
# SDK ``normalize_stream_event(tool_metadata_map=...)`` parameter, whose
# invariant ``dict[str, JsonObject]`` type rejects a narrower ``object`` value.
ToolNameMap = dict[str, str]
ToolMetadataMap = dict[str, dict[str, Any]]


class ExecutionManagerLike(SessionManagerLike, Protocol):
    """Callback seam the execution turn loop invokes on its owning manager."""

    async def emit_session_start_event(
        self,
        session: StudioSession,
        *,
        executor: Executor,
        executor_type: str,
        consumed_queued_message_count: int = 0,
    ) -> None: ...

    def consume_queued_messages(self, session: StudioSession) -> int: ...

    def build_tool_contract_maps(
        self,
        executor: Executor,
    ) -> tuple[ToolNameMap, ToolMetadataMap]: ...


__all__ = [
    "ExecutionManagerLike",
    "ToolMetadataMap",
    "ToolNameMap",
]
