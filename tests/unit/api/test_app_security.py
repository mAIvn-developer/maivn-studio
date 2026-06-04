# pyright: strict
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from maivn_studio.api.app import create_app
from maivn_studio.config.models import DiscoveryConfig, StudioConfig, StudioSettings


def test_spa_route_blocks_parent_path_traversal(tmp_path: Path) -> None:
    app = create_app(
        config=StudioConfig(
            studio=StudioSettings(debug=False),
            discovery=DiscoveryConfig(paths=[], exclude=[]),
        ),
        base_path=tmp_path,
    )

    with TestClient(app) as client:
        response = client.get("/..%2F..%2F..%2Fpyproject.toml")

    assert response.status_code == 404
