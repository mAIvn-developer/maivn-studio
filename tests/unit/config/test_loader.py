# pyright: strict

from __future__ import annotations

from pathlib import Path

import pytest

from maivn_studio.config.loader import find_config_file, load_config


def test_find_config_file_uses_start_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config_path.write_text('{"studio": {"port": 9999}}', encoding="utf-8")

    other_dir = tmp_path / "other"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    assert find_config_file(tmp_path) == config_path


def test_find_config_file_does_not_use_hyphen_name(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "maivn-studio.json").write_text("{}", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    assert find_config_file() is None


def test_load_config_from_file(tmp_path: Path) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config_path.write_text('{"studio": {"port": 9001}}', encoding="utf-8")

    config = load_config(config_path)

    assert config.studio.port == 9001


def test_load_config_empty_file_uses_defaults(tmp_path: Path) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config_path.write_text("", encoding="utf-8")

    config = load_config(config_path)

    assert config.studio.host == "127.0.0.1"
    assert config.studio.port == 8080


def test_load_config_variant_private_data(tmp_path: Path) -> None:
    config_path = tmp_path / "maivn_studio.json"
    config_path.write_text(
        (
            '{"apps":[{"id":"app-1","name":"App One","module":"apps.app_one",'
            '"variants":{"with-private-data":{"description":"Variant","private_data":'
            '{"secret_token":"tok-123","email":"app@example.com"}}}}]}'
        ),
        encoding="utf-8",
    )

    config = load_config(config_path)

    variant = config.apps[0].variants["with-private-data"]
    assert variant.private_data == {
        "secret_token": "tok-123",
        "email": "app@example.com",
    }
