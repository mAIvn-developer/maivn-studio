# pyright: strict

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient
from maivn import Agent, Swarm
from maivn_shared import DataDependency

from maivn_studio.api.app import create_app
from maivn_studio.config.models import (
    AppConfig,
    AppVariant,
    DiscoveryConfig,
    PrivateDataField,
    StudioConfig,
    StudioSettings,
)
from maivn_studio.services.app_loader.loader import AppLoader
from maivn_studio.services.app_loader.models import LoadedApp


@dataclass
class _Prompt:
    name: str
    content: str
    description: str = ""
    source: str = "module"
    is_default: bool = True
    structured_output: str | None = None
    variant: str | None = None


class _Tool:
    def __init__(self) -> None:
        self.dependencies = [DataDependency(data_key="serial_number", arg_name="serial_number")]


class _Agent:
    name = "app_agent"
    description = "App agent"

    def list_tools(self) -> list[_Tool]:
        return [_Tool()]


class _AgentNoPrivateDeps:
    name = "app_agent"
    description = "App agent"

    def list_tools(self) -> list[_Tool]:
        return []


class _Swarm:
    name = "app_swarm"

    def __init__(self) -> None:
        self.agents = [_Agent()]


class _Loaded:
    def __init__(self) -> None:
        self.agents = [_Agent()]
        self.swarms = [_Swarm()]
        self.prompts = [_Prompt(name="Prompt", content="Hello")]
        self.default_invocation = None

    def get_agent(self, name: str) -> _Agent | None:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None


class _LoadedNoPrivateSchema:
    def __init__(self) -> None:
        self.agents = [_AgentNoPrivateDeps()]
        self.swarms: list[_Swarm] = []
        self.prompts = [_Prompt(name="Prompt", content="Hello")]
        self.default_invocation = None

    def get_agent(self, name: str) -> _AgentNoPrivateDeps | None:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None


class _Loader:
    def load(
        self, _app: AppConfig, force_reload: bool = False, variant: str | None = None
    ) -> _Loaded:
        _ = force_reload, variant
        return _Loaded()


class _LoaderNoPrivateSchema:
    def load(
        self, _app: AppConfig, force_reload: bool = False, variant: str | None = None
    ) -> _LoadedNoPrivateSchema:
        _ = force_reload, variant
        return _LoadedNoPrivateSchema()


class _LoadedInvalidVariant:
    def __init__(self) -> None:
        self.agents = [_Agent()]
        self.swarms = [_Swarm()]
        self.prompts = [_Prompt(name="Prompt", content="Hello", variant="missing")]
        self.default_invocation = None

    def get_agent(self, name: str) -> _Agent | None:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None


class _LoaderInvalidVariant:
    def load(
        self, _app: AppConfig, force_reload: bool = False, variant: str | None = None
    ) -> _LoadedInvalidVariant:
        _ = force_reload, variant
        return _LoadedInvalidVariant()


class _LoadedWithDefaultInvocation:
    def __init__(self) -> None:
        self.agents = [_Agent()]
        self.swarms = [_Swarm()]
        self.prompts = [_Prompt(name="Prompt", content="Hello")]
        self.default_invocation: dict[str, Any] = {
            "force_final_tool": True,
            "targeted_tools": ["app_agent.memory_lookup"],
            "metadata": {"source": "test-suite", "memory": True},
        }

    def get_agent(self, name: str) -> _Agent | None:
        for agent in self.agents:
            if getattr(agent, "name", None) == name:
                return agent
        return None


class _LoaderWithDefaultInvocation:
    def load(
        self, _app: AppConfig, force_reload: bool = False, variant: str | None = None
    ) -> _LoadedWithDefaultInvocation:
        _ = force_reload, variant
        return _LoadedWithDefaultInvocation()


class _VariantCapturingLoader:
    def __init__(self) -> None:
        self.variants: list[str | None] = []

    def load(
        self, _app: AppConfig, force_reload: bool = False, variant: str | None = None
    ) -> _Loaded:
        _ = force_reload
        self.variants.append(variant)
        return _Loaded()


def _write_app_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "from maivn import Agent\nconfigured_agent = Agent()\n",
        encoding="utf-8",
    )


def test_apps_endpoints(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        list_resp = client.get("/api/apps")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 1
        assert data["apps"][0]["source"] == "configured"

        get_resp = client.get("/api/apps/app-1")
        assert get_resp.status_code == 200
        assert get_resp.json()["app"]["id"] == "app-1"
        assert get_resp.json()["app"]["source"] == "configured"

        detail_resp = client.get("/api/apps/app-1/details")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["id"] == "app-1"
        assert detail["source"] == "configured"
        assert detail["agents"]
        assert detail["agents"][0]["included_nested_synthesis"] == "auto"
        assert detail["tools"]
        assert any(field["key"] == "serial_number" for field in detail["privateDataSchema"])

        categories_resp = client.get("/api/apps/categories")
        assert categories_resp.status_code == 200
        assert "examples" in categories_resp.json()


def test_configured_app_wins_over_discovered_duplicate_by_module(tmp_path: Path) -> None:
    app_file = tmp_path / "apps" / "app_one.py"
    _write_app_file(app_file)

    configured_app = AppConfig(
        id="configured-app",
        name="Configured App",
        description="Configured version should win",
        module="apps.app_one",
        category="configured",
        tags=["manual"],
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=["apps"], exclude=[]),
        apps=[configured_app],
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        list_resp = client.get("/api/apps")
        assert list_resp.status_code == 200
        data = list_resp.json()

    assert data["total"] == 1
    assert len(data["apps"]) == 1
    assert data["apps"][0]["id"] == "configured-app"
    assert data["apps"][0]["name"] == "Configured App"
    assert data["apps"][0]["source"] == "configured"
    assert data["apps"][0]["module"] == "apps.app_one"


def test_multiple_configured_apps_can_share_module(tmp_path: Path) -> None:
    shared_module = "apps.app_one"
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[
            AppConfig(
                id="app-product",
                name="App Product",
                description="First configured entry",
                module=shared_module,
                category="configured",
            ),
            AppConfig(
                id="app-newsletter",
                name="App Newsletter",
                description="Second configured entry",
                module=shared_module,
                category="configured",
                variants={"newsletter": AppVariant(args=["--newsletter"], description="Variant")},
                default_variant="newsletter",
            ),
        ],
    )

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app) as client:
        list_resp = client.get("/api/apps")
        assert list_resp.status_code == 200
        data = list_resp.json()

    assert data["total"] == 2
    assert {a["id"] for a in data["apps"]} == {"app-product", "app-newsletter"}


def test_update_agent_included_nested_synthesis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _Loader())

    with TestClient(app) as client:
        true_resp = client.patch(
            "/api/apps/app-1/agents/app_agent",
            json={"included_nested_synthesis": True},
        )
        assert true_resp.status_code == 200
        assert true_resp.json()["included_nested_synthesis"] is True

        auto_resp = client.patch(
            "/api/apps/app-1/agents/app_agent",
            json={"included_nested_synthesis": "auto"},
        )
        assert auto_resp.status_code == 200
        assert auto_resp.json()["included_nested_synthesis"] == "auto"


def test_app_details_invalid_prompt_variant_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
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

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _LoaderInvalidVariant())

    with TestClient(app) as client:
        with caplog.at_level("WARNING"):
            detail_resp = client.get("/api/apps/app-1/details")

        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["prompts"][0]["variant"] is None
        assert "Ignoring invalid prompt variant" in caplog.text


def test_app_details_uses_default_variant_when_loading(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
        variants={"fast": AppVariant(args=[], description="Fast variant")},
        default_variant="fast",
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    loader = _VariantCapturingLoader()
    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: loader)

    with TestClient(app) as client:
        detail_resp = client.get("/api/apps/app-1/details")
        assert detail_resp.status_code == 200

    assert loader.variants == ["fast"]


def test_app_details_uses_requested_variant_and_merges_private_data_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
        private_data={"customer_name": "Acme Health", "region": "us"},
        variants={
            "with-private-data": AppVariant(
                args=[],
                description="Variant with private data",
                private_data={"customer_name": "Umbra Labs", "case_id": "CASE-42"},
            )
        },
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    loader = _VariantCapturingLoader()
    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: loader)

    with TestClient(app) as client:
        detail_resp = client.get("/api/apps/app-1/details?variant=with-private-data")
        assert detail_resp.status_code == 200

    assert loader.variants == ["with-private-data"]
    assert detail_resp.json()["privateDataDefaults"] == {
        "customer_name": "Umbra Labs",
        "region": "us",
        "case_id": "CASE-42",
    }
    schema_by_key = {field["key"]: field for field in detail_resp.json()["privateDataSchema"]}
    assert schema_by_key["customer_name"]["default_value"] == "Umbra Labs"
    assert schema_by_key["region"]["default_value"] == "us"
    assert schema_by_key["case_id"]["default_value"] == "CASE-42"


def test_app_details_builds_schema_from_configured_private_data_when_loader_has_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
        variants={
            "with-private-data": AppVariant(
                args=[],
                description="Variant with private data",
                private_data={
                    "email": "studio-think-private@maivn.dev",
                    "secret_token": "THINK-PRIVATE-TOKEN-7302",
                    "case_id": "THINK-CASE-7302",
                },
            )
        },
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _LoaderNoPrivateSchema())

    with TestClient(app) as client:
        detail_resp = client.get("/api/apps/app-1/details?variant=with-private-data")
        assert detail_resp.status_code == 200

    schema_by_key = {field["key"]: field for field in detail_resp.json()["privateDataSchema"]}
    assert schema_by_key["email"]["default_value"] == "studio-think-private@maivn.dev"
    assert schema_by_key["email"]["type"] == "string"
    assert schema_by_key["secret_token"]["default_value"] == "THINK-PRIVATE-TOKEN-7302"
    assert schema_by_key["case_id"]["default_value"] == "THINK-CASE-7302"


def test_merge_private_data_schema_keeps_string_type_when_default_is_none() -> None:
    from maivn_studio.api.routes.apps.routes import merge_private_data_schema

    merged = merge_private_data_schema(
        [
            PrivateDataField(
                key="api_key",
                type="",
                default_value=None,
            )
        ],
        {},
    )

    assert merged[0].default_value is None
    assert merged[0].type == "string"


def test_app_details_includes_default_invocation_targeted_tools_and_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    app = create_app(config=config, base_path=tmp_path)

    import maivn_studio.api.routes.apps.routes as apps_routes

    monkeypatch.setattr(apps_routes, "get_app_loader", lambda: _LoaderWithDefaultInvocation())

    with TestClient(app) as client:
        detail_resp = client.get("/api/apps/app-1/details")

        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["defaultInvocation"] is not None
        assert detail["defaultInvocation"]["targeted_tools"] == ["app_agent.memory_lookup"]
        assert detail["defaultInvocation"]["metadata"] == {"source": "test-suite", "memory": True}


def test_app_loader_invocation_config_keeps_targeted_tools_and_metadata() -> None:
    module = ModuleType("test_app_module")
    module_any = cast(Any, module)
    module_any.APP_INVOCATION = {
        "force_final_tool": True,
        "model": "test-model",
        "reasoning": {"effort": "medium"},
        "targeted_tools": ["app_agent.memory_lookup"],
        "metadata": {"source": "test-suite"},
        "system_tools_config": {"allowed_tools": ["web_search"]},
        "orchestration_config": {"max_cycles": 2},
        "allow_private_in_system_tools": True,
        "unexpected_key": "ignored",
    }

    loader = AppLoader()
    invocation = loader.find_invocation_config(module)

    assert invocation == {
        "force_final_tool": True,
        "model": "test-model",
        "reasoning": {"effort": "medium"},
        "targeted_tools": ["app_agent.memory_lookup"],
        "metadata": {"source": "test-suite"},
        "system_tools_config": {"allowed_tools": ["web_search"]},
        "orchestration_config": {"max_cycles": 2},
        "allow_private_in_system_tools": True,
    }


def test_app_lifespan_shuts_down_session_manager(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app_config = AppConfig(
        id="app-1",
        name="App One",
        description="App description",
        module="apps.app_one",
        category="examples",
        tags=["agent"],
    )
    config = StudioConfig(
        studio=StudioSettings(debug=False),
        discovery=DiscoveryConfig(paths=[], exclude=[]),
        apps=[app_config],
    )

    class _ShutdownManager:
        def __init__(self) -> None:
            self.shutdown_calls = 0

        async def shutdown(self) -> None:
            self.shutdown_calls += 1

    manager = _ShutdownManager()

    import maivn_studio.api.app as app_module

    monkeypatch.setattr(app_module, "get_session_manager", lambda: manager)

    app = create_app(config=config, base_path=tmp_path)

    with TestClient(app):
        pass

    assert manager.shutdown_calls == 1


def test_loaded_app_prefers_explicit_executor_over_default_swarm() -> None:
    loaded = LoadedApp(
        config=AppConfig(id="app-1", name="App", module="apps.app_one"),
        module=ModuleType("test_app_module"),
        agents=[cast(Agent, _Agent())],
        swarms=[cast(Swarm, _Swarm())],
        explicit_executor_name="app_agent",
    )

    assert loaded.executor is loaded.agents[0]
    assert loaded.executor_type == "agent"
    assert loaded.executor_name == "app_agent"
