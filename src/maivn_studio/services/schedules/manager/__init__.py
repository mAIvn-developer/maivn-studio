"""Schedule manager package.

Re-exports the public surface — :class:`ScheduleManager` and the
singleton accessor :func:`get_schedule_manager` — so callers can keep
importing from ``maivn_studio.services.schedules.manager``.
"""

from __future__ import annotations

from .core import ScheduleManager, get_schedule_manager

__all__ = ["ScheduleManager", "get_schedule_manager"]
