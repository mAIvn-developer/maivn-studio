"""Typed view over the FastAPI application state for the Studio API."""

# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import cast

from fastapi import Request

from maivn_studio.config.models import StudioConfig

# MARK: Application State


@dataclass(frozen=True)
class AppState:
    """Typed view over ``request.app.state`` for the Studio API.

    FastAPI stores ``config``/``base_path``/``config_path`` on the loosely-typed
    ``Starlette.State`` bag. This dataclass tightens reads back into concrete
    types at the boundary; writes go through ``app.state`` directly.
    """

    config: StudioConfig
    base_path: Path
    config_path: Path | None


def get_app_state(request: Request) -> AppState:
    """Read the typed Studio application state from a request."""
    state = request.app.state
    return AppState(
        config=cast(StudioConfig, state.config),
        base_path=cast(Path, state.base_path),
        config_path=cast("Path | None", getattr(state, "config_path", None)),
    )
