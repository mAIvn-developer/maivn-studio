from __future__ import annotations

import json

from maivn_studio.config.loader import save_config, set_config
from maivn_studio.config.models import StudioConfig, StudioSettings


def test_save_config_writes_schema(tmp_path) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config = StudioConfig(studio=StudioSettings(port=9002))

    set_config(config, config_path)
    save_config(config)

    data = json.loads(config_path.read_text(encoding="utf-8"))
    assert data["$schema"] == "https://maivn.dev/schema/studio.json"
    assert data["studio"]["port"] == 9002
