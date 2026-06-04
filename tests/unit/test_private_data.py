# pyright: strict

from __future__ import annotations

from pathlib import Path

import pytest
from maivn_shared import DataDependency

from maivn_studio.private_data import (
    extract_private_data_schema,
    get_default_private_data,
    reset_default_private_data,
)


class _Tool:
    def __init__(self, dependencies: list[DataDependency]) -> None:
        self.dependencies = dependencies


class _Scope:
    def __init__(self, tools: list[_Tool]) -> None:
        self._tools = tools

    def list_tools(self) -> list[_Tool]:
        return self._tools


class _Loaded:
    def __init__(self, agents: list[_Scope], swarms: list[_Scope]) -> None:
        self.agents = agents
        self.swarms = swarms


def test_default_private_data_uses_repo_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    log_file = log_dir / "server_execution.log"
    log_file.write_text("ok", encoding="utf-8")

    monkeypatch.chdir(tmp_path)
    reset_default_private_data()

    defaults = get_default_private_data()

    assert defaults["log_path"] == str(log_file)


def test_extract_private_data_schema_collects_dependencies() -> None:
    dependencies = [DataDependency(data_key="serial_number", arg_name="serial_number")]
    tool = _Tool(dependencies)
    scope = _Scope([tool])
    loaded = _Loaded([scope], [])

    schema = extract_private_data_schema(loaded)

    assert any(field.key == "serial_number" for field in schema)
