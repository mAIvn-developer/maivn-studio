# pyright: strict
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import maivn_studio.api.app as app_module
from maivn_studio.api.app import create_app
from maivn_studio.config.models import AppConfig, DiscoveryConfig, StudioConfig, StudioSettings


def test_prompts_crud(tmp_path: Path) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config_path.write_text("{}", encoding="utf-8")

    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        list_resp = client.get("/api/prompts")
        assert list_resp.status_code == 200
        assert list_resp.json() == []

        payload = {
            "name": "Test Prompt",
            "content": "Hello",
            "app_id": "app-1",
            "message_type": "human",
        }
        create_resp = client.post("/api/prompts", json=payload)
        assert create_resp.status_code == 200
        created: dict[str, Any] = create_resp.json()
        assert created["name"] == payload["name"]

        list_resp = client.get("/api/prompts?app_id=app-1")
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1

        delete_resp = client.delete(f"/api/prompts/{created['id']}")
        assert delete_resp.status_code == 200

    saved: dict[str, Any] = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["saved_prompts"] == []


def test_favicon_routes_register_and_serve(tmp_path: Path) -> None:
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    route_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert "/favicon.svg" in route_paths
    assert "/favicon.png" in route_paths
    assert "/favicon.ico" in route_paths

    with TestClient(app) as client:
        png_resp = client.get("/favicon.png")
        assert png_resp.status_code == 200
        assert png_resp.headers["content-type"].startswith("image/png")

        svg_resp = client.get("/favicon.svg", follow_redirects=False)
        assert svg_resp.status_code in (200, 307)
        if svg_resp.status_code == 307:
            assert svg_resp.headers["location"] == "/favicon.png"


def test_app_shutdown_invokes_session_manager_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shutdown_calls: list[str] = []

    class _Manager:
        async def shutdown(self) -> None:
            shutdown_calls.append("shutdown")

    monkeypatch.setattr(app_module, "get_session_manager", lambda: _Manager())

    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app):
        pass

    assert shutdown_calls == ["shutdown"]


def test_sessions_collection_post_accepts_slashless_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _Registry:
        def __init__(self, app_config: AppConfig) -> None:
            self._app = app_config

        def get(self, app_id: str) -> AppConfig | None:
            if app_id == self._app.id:
                return self._app
            return None

    class _Session:
        session_id = "session-1"

        def to_dict(self) -> dict[str, object]:
            return {
                "session_id": "session-1",
                "app_id": "app-1",
                "app_name": "App One",
                "thread_id": "thread-1",
                "variant": None,
                "status": "running",
                "created_at": "2026-03-19T00:00:00",
                "started_at": None,
                "completed_at": None,
                "message_count": 1,
                "can_send_message": True,
                "can_stage_message": False,
                "queued_message_count": 0,
                "is_active": True,
                "error": None,
            }

    class _Manager:
        async def create_session(self, **_: object) -> _Session:
            return _Session()

        async def start_session(self, *_: object, **__: object) -> None:
            return None

        async def shutdown(self) -> None:
            return None

    app_config = AppConfig(id="app-1", name="App One", module="apps.app_one")
    monkeypatch.setattr(
        "maivn_studio.api.routes.sessions.writes.get_registry",
        lambda: _Registry(app_config),
    )
    monkeypatch.setattr(
        "maivn_studio.api.routes.sessions.writes.get_session_manager",
        lambda: _Manager(),
    )

    def _create_event_bridge(_session_id: str) -> None:
        return None

    monkeypatch.setattr(
        "maivn_studio.api.routes.sessions.writes.create_event_bridge",
        _create_event_bridge,
    )

    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        resp = client.post(
            "/api/sessions",
            json={
                "app_id": "app-1",
                "message": "Inspect laptop",
            },
        )

    assert resp.status_code == 200
    assert resp.json()["session_id"] == "session-1"
