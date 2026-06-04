# pyright: strict

from __future__ import annotations

import sys
import zipfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_wheel_contents.py <wheel-path>", file=sys.stderr)
        return 1

    wheel_path = Path(sys.argv[1]).resolve()
    if not wheel_path.is_file():
        print(f"Wheel not found: {wheel_path}", file=sys.stderr)
        return 1

    with zipfile.ZipFile(wheel_path) as archive:
        names = set(archive.namelist())

    required = {
        "maivn_studio/static/index.html",
        "maivn_studio/static/favicon.png",
        "maivn_studio/static/robots.txt",
    }
    missing = sorted(path for path in required if path not in names)
    if missing:
        print("Wheel is missing required Studio assets:", file=sys.stderr)
        for path in missing:
            print(f"  - {path}", file=sys.stderr)
        return 1

    if not any(name.startswith("maivn_studio/static/_app/") for name in names):
        print("Wheel is missing the built SvelteKit _app bundle.", file=sys.stderr)
        return 1

    if not any(name.endswith(".dist-info/entry_points.txt") for name in names):
        print("Wheel is missing the console-script entry points metadata.", file=sys.stderr)
        return 1

    print(f"Wheel contents validated: {wheel_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
