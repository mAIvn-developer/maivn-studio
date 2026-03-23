"""Session management for demo execution.

Submodules:
- manager: SessionManager coordinator and global accessor
- lifecycle: session creation, start/send/end/cancel helpers
- execution: executor invocation and turn orchestration helpers
- events: SSE event emission helpers
- messages: message creation, queue management, and turn config helpers
- models: StudioSession, SessionStatus, and queue data structures
- private_data: private-data application helpers
"""

from __future__ import annotations

from . import events, execution, lifecycle, manager, messages, models, private_data

__all__ = [
    "events",
    "execution",
    "lifecycle",
    "manager",
    "messages",
    "models",
    "private_data",
]
