"""Extended tests for app API routes covering update endpoints and error cases."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from maivn_shared import DataDependency

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
    def __init__(self, deps: list | None = None) -> None:
        self.dependencies = deps or [
            DataDependency(data_key="serial_number", arg_name="serial_number")
        ]


class _Agent:
    name = "app_agent"
    description = "App agent"
    system_prompt = "You are an app agent."
    tags: list[str] = []
    timeout: float | None = None
    max_results: int | None = None
    included_nested_synthesis: bool | str = "auto"
    allow_private_in_system_tools: bool = False
    private_data: dict[str, Any] = {}
    before_execute = None
    after_execute = None
    hook_execution_mode = "tool"
    use_as_final_output = False

    def list_tools(self) -> list:
        return [_Tool()]

    def list_mcp_servers(self) -> list:
        return []


class _Swarm:
    name = "app_swarm"
    description = "App swarm"
    system_prompt = None
    tags: list[str] = []
    allow_private_in_system_tools = False
    private_data: dict[str, Any] = {}

    def __init__(self) -> None:
        self.agents = [_Agent()]

    def list_tools(self) -> list:
        tools = []
        for agent in self.agents:
            tools.extend(agent.list_tools())
        return tools


class _Loaded:
    def __init__(self) -> None:
        self.agents = [_Agent()]
        self.swarms = [_Swarm()]
        self.prompts = [
            _Prompt(name="Default Prompt", content="Hello world"),
            _Prompt(name="Alt Prompt", content="Goodbye", is_default=False, message_type="human"),
        ]
        self.default_invocation = None

    def get_agent(self, name: str) -> Any:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None

    def get_swarm(self, name: str) -> Any:
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
    name = "standalone_agent"

    def list_tools(self) -> list:
        return [_Tool(), _Tool()]


class _SwarmMemberAgent(_Agent):
    name = "swarm_member"

    def list_tools(self) -> list:
        return [_Tool(), _Tool(), _Tool()]


class _MixedSwarm(_Swarm):
    def __init__(self) -> None:
        self.agents = [_SwarmMemberAgent()]


class _MixedLoaded(_Loaded):
    def __init__(self) -> None:
        self.agents = [_StandaloneAgent(), _SwarmMemberAgent()]
        self.swarms = [_MixedSwarm()]
        self.prompts = [_Prompt(name="Default Prompt", content="Hello world")]
        self.default_invocation = None


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


# MARK: Fixtures


def _make_app(tmp_path, app_config: AppConfig | None = None):
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


def test_get_app_full_details_returns_agents_swarms_tools_prompts(monkeypatch, tmp_path) -> None:
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
    monkeypatch, tmp_path
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


def test_get_app_full_details_not_found(monkeypatch, tmp_path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.get("/api/apps/nonexistent/details")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# MARK: Update App Endpoint


def test_update_app_name_description_category(monkeypatch, tmp_path) -> None:
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


def test_update_app_tags_and_private_data(monkeypatch, tmp_path) -> None:
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


def test_update_app_variants(monkeypatch, tmp_path) -> None:
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


def test_update_app_not_found(monkeypatch, tmp_path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch("/api/apps/nonexistent", json={"name": "x"})
        assert resp.status_code == 404


def test_update_app_appends_when_not_found_in_config(monkeypatch, tmp_path) -> None:
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


def test_update_agent_fields(monkeypatch, tmp_path) -> None:
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


def test_update_agent_clear_system_prompt(monkeypatch, tmp_path) -> None:
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


def test_update_agent_not_found(monkeypatch, tmp_path) -> None:
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


def test_update_agent_app_not_found(monkeypatch, tmp_path) -> None:
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


def test_update_agent_memory_config(monkeypatch, tmp_path) -> None:
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


def test_update_swarm_fields(monkeypatch, tmp_path) -> None:
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


def test_update_swarm_clear_system_prompt(monkeypatch, tmp_path) -> None:
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


def test_update_swarm_memory_config(monkeypatch, tmp_path) -> None:
    app, _ = _make_app(tmp_path)
    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        resp = client.patch(
            "/api/apps/app-1/swarms/app_swarm",
            json={"memory_config": {"enabled": True}},
        )
        assert resp.status_code == 200


def test_update_swarm_not_found(monkeypatch, tmp_path) -> None:
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


def test_update_swarm_app_not_found(monkeypatch, tmp_path) -> None:
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
