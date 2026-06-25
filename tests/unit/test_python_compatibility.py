# pyright: strict

from __future__ import annotations

import ast
from pathlib import Path


def test_runtime_code_uses_typing_extensions_for_override() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src" / "maivn_studio"
    offenders: list[str] = []

    for path in source_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom) or node.module != "typing":
                continue
            if any(alias.name == "override" for alias in node.names):
                offenders.append(str(path.relative_to(source_root)))

    assert offenders == []
