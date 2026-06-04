# pyright: strict

from __future__ import annotations

from pathlib import Path

from maivn_studio.discovery.scanner import build_app_config, scan_repo_for_apps


def _write_app_file(path: Path) -> None:
    path.write_text(
        '"""App description."""\n'
        "from maivn import Agent\n"
        "app_agent = Agent()\n"
        "\n"
        "def main():\n"
        "    import argparse\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_argument('--fast', help='Fast mode')\n",
        encoding="utf-8",
    )


def test_build_app_config_extracts_metadata(tmp_path: Path) -> None:
    app_path = tmp_path / "apps" / "feature_app.py"
    app_path.parent.mkdir(parents=True)
    _write_app_file(app_path)

    app = build_app_config(app_path, tmp_path, "apps/features")

    assert app is not None
    assert app.id == "feature"
    assert app.name == "Feature"
    assert app.category == "features"
    assert app.description == "App description."
    assert "agent" in app.tags
    assert "fast" in app.variants


def test_scan_repo_for_apps_respects_excludes(tmp_path: Path) -> None:
    app_path = tmp_path / "apps" / "app_one.py"
    app_path.parent.mkdir(parents=True)
    _write_app_file(app_path)

    excluded_path = tmp_path / "node_modules" / "app_hidden.py"
    excluded_path.parent.mkdir(parents=True)
    _write_app_file(excluded_path)

    items = scan_repo_for_apps(
        base_path=tmp_path,
        discovery_paths=["apps", "node_modules"],
        exclude_patterns=[],
    )

    assert len(items) == 1
    assert Path(str(items[0]["file_path"])).as_posix() == "apps/app_one.py"


def test_scan_repo_for_apps_ignores_paths_outside_base(tmp_path: Path) -> None:
    outside_dir = tmp_path.parent / "outside-apps"
    outside_dir.mkdir(exist_ok=True)
    outside_app = outside_dir / "outside_app.py"
    _write_app_file(outside_app)

    items = scan_repo_for_apps(
        base_path=tmp_path,
        discovery_paths=["../outside-apps"],
        exclude_patterns=[],
    )

    assert items == []
