"""Demo discovery and registry.

Submodules:
- registry: DemoRegistry and global registry accessors
- scanner: repo scanning and demo-config discovery helpers
"""

from __future__ import annotations

from . import registry, scanner

__all__ = ["registry", "scanner"]
