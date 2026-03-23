"""Demo management API routes.

Submodules:
- routes: demo listing, detail, and update endpoints
- models: request/response models for demo endpoints
- introspection: helpers for agent/swarm/tool summary construction
"""

from __future__ import annotations

from . import introspection, models, routes

__all__ = ["introspection", "models", "routes"]
