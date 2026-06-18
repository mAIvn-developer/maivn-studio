"""Extended tests for app API routes covering update endpoints and error cases."""

# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from maivn_shared import DataDependency, SystemMessage

from maivn_studio.api.app import create_app
from maivn_studio.config.models import (
    AppConfig,
    AppVariant,
    DiscoveryConfig,
    StudioConfig,
    StudioSettings,
)

# MARK: Fake SDK Objects


@dataclass
class _Prompt:
    name: str
    content: str
    description: str = ""
    source: str = "module"
    is_default: bool = True
    structured_output: str | None = None
    message_type: str | None = None
    variant: str | None = None


class _Tool:
    def __init__(self, deps: list[DataDependency] | None = None) -> None:
        self.dependencies: list[DataDependency] = deps or [
            DataDependency(data_key="serial_number", arg_name="serial_number")
        ]


class _Agent:
    name: str = "app_agent"
    description: str = "App agent"
    system_prompt: str | None = "You are an app agent."
    tags: list[str] = []
    timeout: float | None = None
    max_results: int | None = None
    included_nested_synthesis: bool | str = "auto"
    allow_private_in_system_tools: bool = False
    private_data: dict[str, Any] = {}
    before_execute: object = None
    after_execute: object = None
    hook_execution_mode: str = "tool"
    use_as_final_output: bool = False
    _system_message: SystemMessage | None = None

    def set_system_message(self, system_prompt: str | SystemMessage | None) -> None:
        """Mirror the SDK's public ``set_system_message`` normalization."""
        if isinstance(system_prompt, str):
            self._system_message = SystemMessage(content=system_prompt)
        elif isinstance(system_prompt, SystemMessage):
            self._system_message = system_prompt
        else:
            self._system_message = None

    def list_tools(self) -> list[_Tool]:
        return [_Tool()]

    def list_mcp_servers(self) -> list[object]:
        return []


class _Swarm:
    name: str = "app_swarm"
    description: str = "App swarm"
    system_prompt: str | None = None
    tags: list[str] = []
    allow_private_in_system_tools: bool = False
    private_data: dict[str, Any] = {}
    _system_message: SystemMessage | None = None

    def __init__(self) -> None:
        self.agents: list[_Agent] = [_Agent()]

    def set_system_message(self, system_prompt: str | SystemMessage | None) -> None:
        """Mirror the SDK's public ``set_system_message`` normalization."""
        if isinstance(system_prompt, str):
            self._system_message = SystemMessage(content=system_prompt)
        elif isinstance(system_prompt, SystemMessage):
            self._system_message = system_prompt
        else:
            self._system_message = None

    def list_tools(self) -> list[_Tool]:
        tools: list[_Tool] = []
        for agent in self.agents:
            tools.extend(agent.list_tools())
        return tools


class _Loaded:
    def __init__(self) -> None:
        self.agents: list[_Agent] = [_Agent()]
        self.swarms: list[_Swarm] = [_Swarm()]
        self.prompts: list[_Prompt] = [
            _Prompt(name="Default Prompt", content="Hello world"),
            _Prompt(name="Alt Prompt", content="Goodbye", is_default=False, message_type="human"),
        ]
        self.default_invocation: dict[str, object] | None = None

    def get_agent(self, name: str) -> _Agent | None:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None

    def get_swarm(self, name: str) -> _Swarm | None:
        for swarm in self.swarms:
            if getattr(swarm, "name", None) == name:
                return swarm
        return None


class _Loader:
    def load(
        self,
        _app: Any,
        force_reload: bool = False,
        variant: str | None = None,
    ) -> _Loaded:
        _ = force_reload, variant
        return _Loaded()

    def unload(self, _app_id: str) -> None:
        pass


# MARK: Mixed Runtime Tool Count Fixtures


class _StandaloneAgent(_Agent):
    name: str = "standalone_agent"

    def list_tools(self) -> list[_Tool]:
        return [_Tool(), _Tool()]


class _SwarmMemberAgent(_Agent):
    name: str = "swarm_member"

    def list_tools(self) -> list[_Tool]:
        return [_Tool(), _Tool(), _Tool()]


class _MixedSwarm(_Swarm):
    def __init__(self) -> None:
        self.agents: list[_Agent] = [_SwarmMemberAgent()]


class _MixedLoaded(_Loaded):
    def __init__(self) -> None:
        self.agents: list[_Agent] = [_StandaloneAgent(), _SwarmMemberAgent()]
        self.swarms: list[_Swarm] = [_MixedSwarm()]
        self.prompts: list[_Prompt] = [_Prompt(name="Default Prompt", content="Hello world")]
        self.default_invocation: dict[str, object] | None = None


class _MixedLoader:
    def load(
        self,
        _app: Any,
        force_reload: bool = False,
        variant: str | None = None,
    ) -> _MixedLoaded:
        _ = force_reload, variant
        return _MixedLoaded()

    def unload(self, _app_id: str) -> None:
        pass


class _FailingLoader:
    def load(
        self,
        _app: Any,
        force_reload: bool = False,
        variant: str | None = None,
    ) -> _Loaded:
        _ = force_reload, variant
        from maivn_studio.services.app_loader.errors import AppLoadError

        raise AppLoadError(
            "demos.toolsets.maivn_tools_gmail_demo",
            ModuleNotFoundError("No module named 'maivn_tools'"),
        )

    def unload(self, _app_id: str) -> None:
        pass


# MARK: Fixtures


def _make_app(tmp_path: Path, app_config: AppConfig | None = None) -> tuple[FastAPI, AppConfig]:
    if app_config is None:
        app_config = AppConfig(
            id="app-1",
            name="App One",
            description="A test app",
            module="apps.app_one",
            category="examples",
            tags=["agent"],
            variants={"fast": AppVariant(args=[], description="Fast variant")},
        )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )
    return create_app(config=config, base_path=tmp_path), app_config


# MARK: Full Details Endpoint


def test_get_app_full_details_returns_agents_swarms_tools_prompts(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.get("/api/apps/app-1/details")
        assert resp.status_code == 200
        detail = resp.json()

        # Agents
        assert len(detail["agents"]) == 1
        agent = detail["agents"][0]
        assert agent["name"] == "app_agent"
        assert agent["description"] == "App agent"
        assert agent["system_prompt"] == "You are an app agent."
        assert agent["tool_count"] == 1
        assert agent["runtime_tool_count"] == 1
        assert agent["is_swarm_member"] is True
        assert agent["swarm"] == "app_swarm"

        # Swarms
        assert len(detail["swarms"]) == 1
        swarm = detail["swarms"][0]
        assert swarm["name"] == "app_swarm"
        assert swarm["agent_count"] == 1
        assert swarm["agent_names"] == ["app_agent"]
        assert swarm["tool_count"] == 1
        assert swarm["runtime_tool_count"] == 1

        # Tools
        assert len(detail["tools"]) >= 1

        # Prompts
        assert len(detail["prompts"]) == 2
        assert detail["prompts"][0]["name"] == "Default Prompt"
        assert detail["prompts"][0]["is_default"] is True
        assert detail["prompts"][1]["name"] == "Alt Prompt"
        assert detail["prompts"][1]["message_type"] == "human"

        # Private data schema
        assert any(f["key"] == "serial_number" for f in detail["privateDataSchema"])

        # Variants
        assert "fast" in detail["variants"]
        assert detail["runtime_tool_count"] == 1


def test_get_app_full_details_runtime_tool_count_excludes_swarm_member_agents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _MixedLoader())

    with TestClient(app) as client:
        resp = client.get("/api/apps/app-1/details")
        assert resp.status_code == 200
        detail = resp.json()

        assert len(detail["agents"]) == 2
        assert len(detail["swarms"]) == 1
        assert detail["runtime_tool_count"] == 5


def test_get_app_full_details_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.get("/api/apps/nonexistent/details")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


def test_get_app_full_details_returns_unloadable_response_for_missing_dependency(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _FailingLoader())

    with TestClient(app) as client:
        resp = client.get("/api/apps/app-1/details")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["loadable"] is False
        assert detail["missing_modules"] == ["maivn_tools"]
        assert "maivn_tools" in detail["load_error"]
        assert detail["agents"] == []
        assert detail["tools"] == []


# MARK: Update App Endpoint


def test_update_app_name_description_category(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    mock_config = MagicMock()
    mock_config.apps = [
        AppConfig(
            id="app-1",
            name="App One",
            module="apps.app_one",
            category="examples",
        )
    ]

    with (
        patch("maivn_studio.config.loader.get_config", return_value=mock_config),
        patch("maivn_studio.config.loader.save_config"),
    ):
        with TestClient(app) as client:
            resp = client.patch(
                "/api/apps/app-1",
                json={
                    "name": "Updated App",
                    "description": "New description",
                    "category": "updated",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["app"]["name"] == "Updated App"
            assert data["app"]["description"] == "New description"
            assert data["app"]["category"] == "updated"


def test_update_app_tags_and_private_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    mock_config = MagicMock()
    mock_config.apps = [
        AppConfig(
            id="app-1",
            name="App One",
            module="apps.app_one",
        )
    ]

    with (
        patch("maivn_studio.config.loader.get_config", return_value=mock_config),
        patch("maivn_studio.config.loader.save_config"),
    ):
        with TestClient(app) as client:
            resp = client.patch(
                "/api/apps/app-1",
                json={
                    "tags": ["new-tag", "another-tag"],
                    "private_data": {"api_key": "secret123"},
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["app"]["tags"] == ["new-tag", "another-tag"]
            assert data["app"]["private_data"] == {"api_key": "secret123"}


def test_update_app_variants(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    mock_config = MagicMock()
    mock_config.apps = [AppConfig(id="app-1", name="App One", module="apps.app_one")]

    with (
        patch("maivn_studio.config.loader.get_config", return_value=mock_config),
        patch("maivn_studio.config.loader.save_config"),
    ):
        with TestClient(app) as client:
            resp = client.patch(
                "/api/apps/app-1",
                json={
                    "variants": {
                        "turbo": {"args": ["--fast"], "description": "Turbo mode"},
                    },
                },
            )
            assert resp.status_code == 200
            assert "turbo" in resp.json()["variants"]


def test_update_app_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch("/api/apps/nonexistent", json={"name": "x"})
        assert resp.status_code == 404


def test_update_app_appends_when_not_found_in_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When the app exists in the registry but not in config.apps, it should be appended."""
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    mock_config = MagicMock()
    # Config has a different app, so for-else will append
    mock_config.apps = [AppConfig(id="other-app", name="Other", module="apps.other")]

    with (
        patch("maivn_studio.config.loader.get_config", return_value=mock_config),
        patch("maivn_studio.config.loader.save_config"),
    ):
        with TestClient(app) as client:
            resp = client.patch(
                "/api/apps/app-1",
                json={"name": "Appended App"},
            )
            assert resp.status_code == 200
            assert resp.json()["app"]["name"] == "Appended App"
            # Verify the app was appended
            assert len(mock_config.apps) == 2


# MARK: Update Agent Endpoint


def test_update_agent_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/agents/app_agent",
            json={
                "description": "Updated agent description",
                "system_prompt": "New system prompt",
                "tags": ["updated"],
                "timeout": 30.0,
                "max_results": 5,
                "allow_private_in_system_tools": True,
                "private_data": {"key": "value"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "app_agent"
        # The description in the response comes from the build_agent_info which reads
        # the mutated agent
        assert data["name"] == "app_agent"


def test_update_agent_clear_system_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/agents/app_agent",
            json={"system_prompt": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["system_prompt"] is None


def test_update_agent_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/agents/nonexistent_agent",
            json={"description": "x"},
        )
        assert resp.status_code == 404
        assert "Agent not found" in resp.json()["detail"]


def test_update_agent_app_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/nonexistent/agents/app_agent",
            json={"description": "x"},
        )
        assert resp.status_code == 404
        assert "App not found" in resp.json()["detail"]


def test_update_agent_memory_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/agents/app_agent",
            json={"memory_config": {"enabled": True}},
        )
        assert resp.status_code == 200


# MARK: Update Swarm Endpoint


def test_update_swarm_fields(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/swarms/app_swarm",
            json={
                "description": "Updated swarm description",
                "system_prompt": "Swarm system prompt",
                "tags": ["swarm-tag"],
                "allow_private_in_system_tools": True,
                "private_data": {"swarm_key": "swarm_value"},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "app_swarm"


def test_update_swarm_clear_system_prompt(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/swarms/app_swarm",
            json={"system_prompt": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["system_prompt"] is None


def test_update_swarm_memory_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/swarms/app_swarm",
            json={"memory_config": {"enabled": True}},
        )
        assert resp.status_code == 200


def test_update_swarm_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/swarms/nonexistent_swarm",
            json={"description": "x"},
        )
        assert resp.status_code == 404
        assert "Swarm not found" in resp.json()["detail"]


def test_update_swarm_app_not_found(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/nonexistent/swarms/app_swarm",
            json={"description": "x"},
        )
        assert resp.status_code == 404
        assert "App not found" in resp.json()["detail"]
