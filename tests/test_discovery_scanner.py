from __future__ import annotations

from pathlib import Path

from maivn_studio.discovery.scanner import build_demo_config, scan_repo_for_demos


def _write_demo_file(path: Path) -> None:
    path.write_text(
        '"""Demo description."""\n'
        "from maivn import Agent\n"
        "demo_agent = Agent()\n"
        "\n"
        "def main():\n"
        "    import argparse\n"
        "    parser = argparse.ArgumentParser()\n"
        "    parser.add_argument('--fast', help='Fast mode')\n",
        encoding="utf-8",
    )


def test_build_demo_config_extracts_metadata(tmp_path) -> None:
    demo_path = tmp_path / "demos" / "feature_demo.py"
    demo_path.parent.mkdir(parents=True)
    _write_demo_file(demo_path)

    demo = build_demo_config(demo_path, tmp_path, "demos/features")

    assert demo is not None
    assert demo.id == "feature"
    assert demo.name == "Feature"
    assert demo.category == "features"
    assert demo.description == "Demo description."
    assert "agent" in demo.tags
    assert "fast" in demo.variants


def test_scan_repo_for_demos_respects_excludes(tmp_path) -> None:
    demo_path = tmp_path / "demos" / "demo_one.py"
    demo_path.parent.mkdir(parents=True)
    _write_demo_file(demo_path)

    excluded_path = tmp_path / "node_modules" / "demo_hidden.py"
    excluded_path.parent.mkdir(parents=True)
    _write_demo_file(excluded_path)

    items = scan_repo_for_demos(
        base_path=tmp_path,
        discovery_paths=["demos", "node_modules"],
        exclude_patterns=[],
    )

    assert len(items) == 1
    assert Path(items[0]["file_path"]).as_posix() == "demos/demo_one.py"


def test_scan_repo_for_demos_ignores_paths_outside_base(tmp_path) -> None:
    outside_dir = tmp_path.parent / "outside-demos"
    outside_dir.mkdir(exist_ok=True)
    outside_demo = outside_dir / "outside_demo.py"
    _write_demo_file(outside_demo)

    items = scan_repo_for_demos(
        base_path=tmp_path,
        discovery_paths=["../outside-demos"],
        exclude_patterns=[],
    )

    assert items == []
