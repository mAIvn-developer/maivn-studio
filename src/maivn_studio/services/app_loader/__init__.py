"""Dynamic app module loading and introspection.

Submodules:
- loader: AppLoader implementation and global loader accessors
- models: LoadedApp and AppPrompt data structures
"""

# pyright: strict
from __future__ import annotations

from . import loader, models

__all__ = ["loader", "models"]
