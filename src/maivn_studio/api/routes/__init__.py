"""API route handlers.

Submodules:
- apps.routes: app-management endpoints
- discovery: repository discovery endpoints
- prompts: saved-prompt endpoints
- sessions.routes: session lifecycle and SSE endpoints
"""

# pyright: strict

from __future__ import annotations

from . import apps, discovery, prompts, sessions

__all__ = ["apps", "discovery", "prompts", "sessions"]
