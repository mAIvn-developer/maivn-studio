"""API route handlers.

Submodules:
- demos.routes: demo-management endpoints
- discovery: repository discovery endpoints
- prompts: saved-prompt endpoints
- sessions.routes: session lifecycle and SSE endpoints
"""

from __future__ import annotations

from . import demos, discovery, prompts, sessions

__all__ = ["demos", "discovery", "prompts", "sessions"]
