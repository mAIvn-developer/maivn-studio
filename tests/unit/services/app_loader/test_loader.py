"""Tests for the AppLoader service."""

# pyright: strict

from __future__ import annotations

from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from maivn import Agent, Swarm

from maivn_studio.config.models import AppConfig
from maivn_studio.services.app_loader.errors import AppLoadError
from maivn_studio.services.app_loader.loader import AppLoader
from maivn_studio.services.app_loader.models import LoadedApp

# MARK: Helpers


def _make_config(**overrides: Any) -> AppConfig:
    defaults: dict[str, Any] = {
        "id": "test-app",
        "name": "Test App",
        "module": "test_module",
    }
    defaults.update(overrides)
    return AppConfig(**defaults)


def _make_module(attrs: dict[str, Any] | None = None, name: str = "fake_mod") -> ModuleType:
    mod = ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    return mod


def _mock_agent(name: str = "agent1", description: str = "") -> Agent:
    agent = Agent.model_construct(name=name, description=description, client=MagicMock())
    return agent


def _mock_swarm(
    name: str = "swarm1", description: str = "", agents: list[Agent] | None = None
) -> Swarm:
    swarm = Swarm.model_construct(name=name, description=description, agents=agents or [])
    return swarm


# MARK: find_agents


class TestFindAgents:
    def test_finds_agent_instances(self) -> None:
        agent = _mock_agent("my_agent")
        mod = _make_module({"my_agent": agent})
        loader = AppLoader()
        result = loader.find_agents(mod)
        assert result == [agent]

    def test_skips_private_attributes(self) -> None:
        agent = _mock_agent("_hidden")
        mod = _make_module({"_hidden": agent})
        loader = AppLoader()
        assert loader.find_agents(mod) == []

    def test_returns_empty_when_no_agents(self) -> None:
        mod = _make_module({"x": 42, "y": "hello"})
        loader = AppLoader()
        assert loader.find_agents(mod) == []


# MARK: find_swarms


class TestFindSwarms:
    def test_finds_swarm_instances(self) -> None:
        swarm = _mock_swarm("my_swarm")
        mod = _make_module({"my_swarm": swarm})
        loader = AppLoader()
        result = loader.find_swarms(mod)
        assert result == [swarm]

    def test_skips_private_attributes(self) -> None:
        swarm = _mock_swarm("_hidden")
        mod = _make_module({"_hidden": swarm})
        loader = AppLoader()
        assert loader.find_swarms(mod) == []

    def test_returns_empty_when_no_swarms(self) -> None:
        mod = _make_module({"x": 42})
        loader = AppLoader()
        assert loader.find_swarms(mod) == []


# MARK: find_prompts


class TestFindPrompts:
    def test_app_prompts_list(self) -> None:
        mod = _make_module(
            {
                "APP_PROMPTS": [
                    {"name": "P1", "content": "Hello", "description": "First prompt"},
                    {"content": "World"},  # minimal dict
                ]
            }
        )
        config = _make_config()
        loader = AppLoader()
        prompts = loader.find_prompts(mod, config)

        assert len(prompts) == 2
        assert prompts[0].name == "P1"
        assert prompts[0].content == "Hello"
        assert prompts[0].is_default is True
        assert prompts[1].name == "Prompt 2"
        assert prompts[1].content == "World"

    def test_default_prompt_string(self) -> None:
        mod = _make_module({"DEFAULT_PROMPT": "Ask me anything"})
        config = _make_config()
        loader = AppLoader()
        prompts = loader.find_prompts(mod, config)

        assert len(prompts) == 1
        assert prompts[0].content == "Ask me anything"
        assert prompts[0].name == "Default Prompt"
        assert prompts[0].is_default is True

    def test_messages_list_with_human_message(self) -> None:
        mod = _make_module({"messages": [HumanMessage(content="Hi there")]})
        config = _make_config()
        loader = AppLoader()
        prompts = loader.find_prompts(mod, config)

        assert len(prompts) == 1
        assert prompts[0].content == "Hi there"
        assert prompts[0].source == "module"

    def test_ignores_invalid_app_prompts(self) -> None:
        mod = _make_module({"APP_PROMPTS": [{"no_content": True}]})
        config = _make_config()
        loader = AppLoader()
        prompts = loader.find_prompts(mod, config)
        # The dict without 'content' key is skipped; falls through to source extraction
        assert all(p.source in ("module", "source") for p in prompts)


# MARK: find_invocation_config


class TestFindInvocationConfig:
    def test_valid_config(self) -> None:
        mod = _make_module(
            {
                "APP_INVOCATION": {
                    "model": "gpt-4",
                    "reasoning": True,
                    "force_final_tool": "my_tool",
                    "system_tools_config": {"allowed_tools": ["web_search"]},
                    "orchestration_config": {"max_cycles": 2},
                    "garbage_key": "ignored",
                }
            }
        )
        loader = AppLoader()
        result = loader.find_invocation_config(mod)

        assert result is not None
        assert result["model"] == "gpt-4"
        assert result["reasoning"] is True
        assert result["force_final_tool"] == "my_tool"
        assert result["system_tools_config"] == {"allowed_tools": ["web_search"]}
        assert result["orchestration_config"] == {"max_cycles": 2}
        assert "garbage_key" not in result

    def test_returns_none_for_non_dict(self) -> None:
        mod = _make_module({"APP_INVOCATION": "not a dict"})
        loader = AppLoader()
        assert loader.find_invocation_config(mod) is None

    def test_returns_none_when_missing(self) -> None:
        mod = _make_module()
        loader = AppLoader()
        assert loader.find_invocation_config(mod) is None


# MARK: find_executor_name


class TestFindExecutorName:
    def test_valid_string(self) -> None:
        mod = _make_module({"APP_EXECUTOR": "my_agent"})
        loader = AppLoader()
        assert loader.find_executor_name(mod) == "my_agent"

    def test_returns_none_for_non_string(self) -> None:
        mod = _make_module({"APP_EXECUTOR": 123})
        loader = AppLoader()
        assert loader.find_executor_name(mod) is None

    def test_returns_none_when_missing(self) -> None:
        mod = _make_module()
        loader = AppLoader()
        assert loader.find_executor_name(mod) is None

    def test_returns_none_for_blank_string(self) -> None:
        mod = _make_module({"APP_EXECUTOR": "   "})
        loader = AppLoader()
        assert loader.find_executor_name(mod) is None


# MARK: load


class TestLoad:
    def test_load_imports_module(self) -> None:
        agent = _mock_agent("a1")
        fake_mod = _make_module({"a1": agent})
        config = _make_config(module="some.module")
        loader = AppLoader()

        with patch("importlib.import_module", return_value=fake_mod) as mock_import:
            loaded = loader.load(config)

        mock_import.assert_called_once_with("some.module")
        assert loaded.agents == [agent]
        assert loaded.config is config

    def test_load_caches_result(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = AppLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            first = loader.load(config)
            second = loader.load(config)

        assert first is second

    def test_load_force_reload(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = AppLoader()

        with patch("maivn_studio.services.app_loader.loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = fake_mod
            mock_importlib.reload.return_value = fake_mod
            loader.load(config)
            loader.load(config, force_reload=True)

        assert mock_importlib.import_module.call_count == 2
        mock_importlib.reload.assert_called_once_with(fake_mod)

    def test_load_with_variant_cache_key(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = AppLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loader.load(config, variant="v1")
            loader.load(config, variant="v2")

        # Different variants get different cache entries
        assert "test-app:v1" in loader.cache
        assert "test-app:v2" in loader.cache

    def test_load_raises_import_error(self) -> None:
        config = _make_config(module="nonexistent.module")
        loader = AppLoader()

        with patch("importlib.import_module", side_effect=ImportError("not found")):
            with pytest.raises(AppLoadError, match="not found"):
                loader.load(config)

    def test_load_wraps_runtime_errors_during_import(self) -> None:
        config = _make_config(module="main")
        loader = AppLoader()

        with patch("importlib.import_module", side_effect=RuntimeError("agent invoke failed")):
            with pytest.raises(AppLoadError, match="agent invoke failed"):
                loader.load(config)

    def test_load_variant_rebuilds_prompts_after_configure_variant(self) -> None:
        module = _make_module(
            {
                "APP_PROMPTS": [{"name": "Default", "content": "generic prompt"}],
            }
        )

        private_prompts: list[dict[str, str]] = [
            {"name": "Private Prompt", "content": "email studio-think-private@maivn.dev"}
        ]
        default_prompts: list[dict[str, str]] = [{"name": "Default", "content": "generic prompt"}]

        def _configure_variant(variant: str | None) -> None:
            chosen = private_prompts if variant == "with-private-data" else default_prompts
            setattr(module, "APP_PROMPTS", chosen)  # noqa: B010 - dynamic ModuleType attribute

        setattr(module, "configure_variant", _configure_variant)  # noqa: B010

        config = _make_config()
        loader = AppLoader()

        with patch("importlib.import_module", return_value=module):
            loaded = loader.load(config, variant="with-private-data")

        assert len(loaded.prompts) == 1
        assert loaded.prompts[0].content == "email studio-think-private@maivn.dev"


# MARK: get and unload


class TestGetAndUnload:
    def test_get_returns_cached(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = AppLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loaded = loader.load(config)

        assert loader.get("test-app") is loaded

    def test_get_returns_none_for_missing(self) -> None:
        loader = AppLoader()
        assert loader.get("nonexistent") is None

    def test_unload_removes_from_cache(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = AppLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loader.load(config)
            loader.load(config, variant="v1")

        assert loader.get("test-app") is not None
        loader.unload("test-app")
        assert loader.get("test-app") is None
        # Variant entries with prefix also removed
        assert "test-app:v1" not in loader.cache


# MARK: apply_variant


class TestApplyVariant:
    def test_calls_configure_variant(self) -> None:
        mock_fn = MagicMock()
        mod = _make_module({"configure_variant": mock_fn})
        loader = AppLoader()
        loader.apply_variant(mod, "v1")
        mock_fn.assert_called_once_with("v1")

    def test_noop_without_configure_variant(self) -> None:
        mod = _make_module()
        loader = AppLoader()
        # Should not raise
        loader.apply_variant(mod, "v1")

    def test_handles_exception_gracefully(self) -> None:
        mock_fn = MagicMock(side_effect=ValueError("boom"))
        mod = _make_module({"configure_variant": mock_fn})
        loader = AppLoader()
        # Should not raise, just log warning
        loader.apply_variant(mod, "v1")


# MARK: LoadedApp.executor


class TestLoadedAppExecutor:
    def test_prefers_explicit_executor(self) -> None:
        agent = _mock_agent("target")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(
            config=config,
            module=mod,
            agents=[agent],
            explicit_executor_name="target",
        )
        assert loaded.executor is agent

    def test_prefers_explicit_executor_by_module_variable_name(self) -> None:
        agent = _mock_agent("Research Coordinator")
        swarm = _mock_swarm("Research Swarm", agents=[agent])
        config = _make_config()
        mod = _make_module({"research_coordinator": agent, "swarm": swarm})
        loaded = LoadedApp(
            config=config,
            module=mod,
            agents=[agent],
            swarms=[swarm],
            explicit_executor_name="research_coordinator",
        )

        assert loaded.executor is agent

    def test_falls_back_to_swarm(self) -> None:
        swarm = _mock_swarm("s1")
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[agent], swarms=[swarm])
        assert loaded.executor is swarm

    def test_falls_back_to_agent(self) -> None:
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[agent])
        assert loaded.executor is agent

    def test_returns_none_when_empty(self) -> None:
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod)
        assert loaded.executor is None


# MARK: LoadedApp.executor_type


class TestLoadedAppExecutorType:
    def test_swarm_type(self) -> None:
        swarm = _mock_swarm("s1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, swarms=[swarm])
        assert loaded.executor_type == "swarm"

    def test_agent_type(self) -> None:
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[agent])
        assert loaded.executor_type == "agent"

    def test_none_type(self) -> None:
        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod)
        assert loaded.executor_type == "none"


# MARK: LoadedApp.get_tools


class TestLoadedAppGetTools:
    def test_collects_tools_from_agents(self) -> None:
        tool_mock = MagicMock()
        tool_mock.name = "my_tool"
        tool_mock.description = "A tool"
        tool_mock.final_tool = False

        repo_mock = MagicMock()
        repo_mock.list_tools.return_value = [tool_mock]

        agent = _mock_agent("a1")
        # Inject the SDK's private tool-repo attribute. ``Agent.list_tools`` reads
        # ``_tool_repo`` (a maivn PrivateAttr); ``setattr`` keeps the assignment off
        # the strict ``reportPrivateUsage`` path for the out-of-scope SDK boundary.
        setattr(agent, "_tool_repo", repo_mock)  # noqa: B010

        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[agent])
        tools = loaded.get_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "my_tool"
        assert tools[0]["agent"] == "a1"

    def test_deduplicates_tools(self) -> None:
        tool_mock = MagicMock()
        tool_mock.name = "shared_tool"
        tool_mock.description = "Shared"
        tool_mock.final_tool = False

        repo = MagicMock()
        repo.list_tools.return_value = [tool_mock]

        a1 = _mock_agent("a1")
        setattr(a1, "_tool_repo", repo)  # noqa: B010 - inject SDK PrivateAttr; see get_tools test
        a2 = _mock_agent("a2")
        setattr(a2, "_tool_repo", repo)  # noqa: B010 - inject SDK PrivateAttr; see get_tools test

        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[a1, a2])
        tools = loaded.get_tools()
        assert len(tools) == 1

    def test_returns_empty_without_tool_repo(self) -> None:
        agent = _mock_agent("a1")

        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[agent])
        assert loaded.get_tools() == []


# MARK: LoadedApp.get_all_agents


class TestLoadedAppGetAllAgents:
    def test_includes_standalone_and_swarm_agents(self) -> None:
        standalone = _mock_agent("standalone", description="Solo")
        member = _mock_agent("member", description="In swarm")
        swarm = _mock_swarm("s1", agents=[member])

        config = _make_config()
        mod = _make_module()
        loaded = LoadedApp(config=config, module=mod, agents=[standalone], swarms=[swarm])
        result = loaded.get_all_agents()

        assert len(result) == 2
        assert result[0]["name"] == "standalone"
        assert result[0]["is_swarm_member"] is False
        assert result[1]["name"] == "member"
        assert result[1]["is_swarm_member"] is True
        assert result[1]["swarm"] == "s1"
