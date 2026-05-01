from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from maivn_studio.api.app import create_app
from maivn_studio.config.models import DiscoveryConfig, StudioConfig, StudioSettings


def _write_app_file(path: Path) -> None:
    path.write_text(
        "from maivn import Agent\napp_agent = Agent()\n",
        encoding="utf-8",
    )


def test_discovery_scan_and_apply(tmp_path) -> None:
    apps_dir = tmp_path / "apps"
    apps_dir.mkdir()
    app_file = apps_dir / "app_one.py"
    _write_app_file(app_file)

    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=["apps"], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        scan_resp = client.post("/api/discovery/scan")
        assert scan_resp.status_code == 200
        scan_data = scan_resp.json()
        assert scan_data["total"] == 1

        first_item = scan_data["items"][0]
        selection = {
            "file_path": first_item["file_path"],
            "discovery_path": first_item["discovery_path"],
        }
        apply_resp = client.post("/api/discovery/apply", json={"selections": [selection]})
        assert apply_resp.status_code == 200
        apply_data = apply_resp.json()
        assert apply_data["added"] == 1

    config_path = tmp_path / "maivn_studio.json"
    assert config_path.exists()
    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["apps"][0]["id"] == "app-one"


def test_discovery_apply_ignores_files_outside_base_path(tmp_path) -> None:
    outside_dir = tmp_path.parent / "outside-apps"
    outside_dir.mkdir(exist_ok=True)
    outside_file = outside_dir / "outside_app.py"
    _write_app_file(outside_file)

    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=["apps"], exclude=[]),
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        apply_resp = client.post(
            "/api/discovery/apply",
            json={
                "selections": [
                    {
                        "file_path": "../outside-apps/outside_app.py",
                        "discovery_path": "../outside-apps",
                    }
                ]
            },
        )

    assert apply_resp.status_code == 200
    assert apply_resp.json() == {"added": 0, "total": 0}
