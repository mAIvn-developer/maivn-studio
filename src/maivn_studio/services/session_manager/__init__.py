# pyright: strict
"""Session management for app execution.

Submodules:
- manager: SessionManager coordinator and global accessor
- lifecycle: session creation, start/send/end/cancel helpers
- execution: executor invocation and turn orchestration helpers
- events: SSE event emission helpers
- messages: message creation, queue management, and turn config helpers
- models: StudioSession, SessionStatus, and queue data structures
- private_data: private-data application helpers
- protocols: shared executor / manager type contracts
"""

from __future__ import annotations

from . import events, execution, lifecycle, manager, messages, models, private_data, protocols

__all__ = [
    "events",
    "execution",
    "lifecycle",
    "manager",
    "messages",
    "models",
    "private_data",
    "protocols",
]
