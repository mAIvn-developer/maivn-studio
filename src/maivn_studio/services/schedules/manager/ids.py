"""Synthetic ID helpers + next-tick prediction for schedule fires."""

# pyright: strict

from __future__ import annotations

from datetime import datetime

from maivn import ScheduledJob


def fire_event_session_id(job_id: str, fire_id: str) -> str:
    """Synthetic session id for a single scheduled fire's event bridge.

    Format is intentionally distinct from real session ids so a stray lookup
    can be diagnosed in logs.
    """
    return f"schedule:{job_id}:{fire_id}"


def app_event_bridge_id(app_id: str) -> str:
    """Synthetic session id for the per-app schedule activity push stream.

    The frontend subscribes to this once per app and learns about new fires
    the moment the SDK's on_fire callback runs — no polling required for the
    countdown -> running transition the user sees on the schedule card.
    """
    return f"schedule-app:{app_id}"


def predict_next_run_iso(job: ScheduledJob, after: datetime) -> str | None:
    """Compute the next scheduled fire strictly after ``after`` using the
    job's schedule and return it as ISO-8601, or ``None`` if no future fire
    exists (one-shot completed, ``max_runs`` reached, etc.).

    Used to populate ``next_run_at`` in push events so the frontend's
    countdown advances the instant a fire starts/completes/skips, instead
    of waiting for the SDK's run loop to iterate plus a reconciliation
    poll. Cheap — croniter just walks the expression forward one tick.
    """
    try:
        nxt = job.schedule.next_after(after)
    except Exception:  # noqa: BLE001 - defensive; never crash the callback
        return None
    return nxt.isoformat() if nxt is not None else None


__all__ = [
    "app_event_bridge_id",
    "fire_event_session_id",
    "predict_next_run_iso",
]
