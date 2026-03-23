"""Dynamic demo module loading and introspection.

Submodules:
- loader: DemoLoader implementation and global loader accessors
- models: LoadedDemo and DemoPrompt data structures
"""

from __future__ import annotations

from . import loader, models

__all__ = ["loader", "models"]
