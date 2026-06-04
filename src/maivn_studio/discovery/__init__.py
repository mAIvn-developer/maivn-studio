"""App discovery and registry.

Submodules:
- registry: AppRegistry and global registry accessors
- scanner: repo scanning and app-config discovery helpers
"""

# pyright: strict

from __future__ import annotations

from . import registry, scanner

__all__ = ["registry", "scanner"]
