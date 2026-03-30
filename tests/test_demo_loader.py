"""Tests for the DemoLoader service."""

from __future__ import annotations

from types import ModuleType
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage
from maivn import Agent, Swarm

from maivn_studio.config.models import DemoConfig
from maivn_studio.services.demo_loader.loader import DemoLoader
from maivn_studio.services.demo_loader.models import LoadedDemo

# MARK: Helpers


def _make_config(**overrides: Any) -> DemoConfig:
    defaults: dict[str, Any] = {
        "id": "test-demo",
        "name": "Test Demo",
        "module": "test_module",
    }
    defaults.update(overrides)
    return DemoConfig(**defaults)


def _make_module(attrs: dict[str, Any] | None = None, name: str = "fake_mod") -> ModuleType:
    mod = ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    return mod


def _mock_agent(name: str = "agent1", description: str = "") -> Agent:
    agent = Agent.model_construct(name=name, description=description, client=MagicMock())
    return agent


def _mock_swarm(name: str = "swarm1", description: str = "", agents: list | None = None) -> Swarm:
    swarm = Swarm.model_construct(name=name, description=description, agents=agents or [])
    return swarm


# MARK: _find_agents


class TestFindAgents:
    def test_finds_agent_instances(self) -> None:
        agent = _mock_agent("my_agent")
        mod = _make_module({"my_agent": agent})
        loader = DemoLoader()
        result = loader._find_agents(mod)
        assert result == [agent]

    def test_skips_private_attributes(self) -> None:
        agent = _mock_agent("_hidden")
        mod = _make_module({"_hidden": agent})
        loader = DemoLoader()
        assert loader._find_agents(mod) == []

    def test_returns_empty_when_no_agents(self) -> None:
        mod = _make_module({"x": 42, "y": "hello"})
        loader = DemoLoader()
        assert loader._find_agents(mod) == []


# MARK: _find_swarms


class TestFindSwarms:
    def test_finds_swarm_instances(self) -> None:
        swarm = _mock_swarm("my_swarm")
        mod = _make_module({"my_swarm": swarm})
        loader = DemoLoader()
        result = loader._find_swarms(mod)
        assert result == [swarm]

    def test_skips_private_attributes(self) -> None:
        swarm = _mock_swarm("_hidden")
        mod = _make_module({"_hidden": swarm})
        loader = DemoLoader()
        assert loader._find_swarms(mod) == []

    def test_returns_empty_when_no_swarms(self) -> None:
        mod = _make_module({"x": 42})
        loader = DemoLoader()
        assert loader._find_swarms(mod) == []


# MARK: _find_prompts


class TestFindPrompts:
    def test_demo_prompts_list(self) -> None:
        mod = _make_module(
            {
                "DEMO_PROMPTS": [
                    {"name": "P1", "content": "Hello", "description": "First prompt"},
                    {"content": "World"},  # minimal dict
                ]
            }
        )
        config = _make_config()
        loader = DemoLoader()
        prompts = loader._find_prompts(mod, config)

        assert len(prompts) == 2
        assert prompts[0].name == "P1"
        assert prompts[0].content == "Hello"
        assert prompts[0].is_default is True
        assert prompts[1].name == "Prompt 2"
        assert prompts[1].content == "World"

    def test_default_prompt_string(self) -> None:
        mod = _make_module({"DEFAULT_PROMPT": "Ask me anything"})
        config = _make_config()
        loader = DemoLoader()
        prompts = loader._find_prompts(mod, config)

        assert len(prompts) == 1
        assert prompts[0].content == "Ask me anything"
        assert prompts[0].name == "Default Prompt"
        assert prompts[0].is_default is True

    def test_messages_list_with_human_message(self) -> None:
        mod = _make_module({"messages": [HumanMessage(content="Hi there")]})
        config = _make_config()
        loader = DemoLoader()
        prompts = loader._find_prompts(mod, config)

        assert len(prompts) == 1
        assert prompts[0].content == "Hi there"
        assert prompts[0].source == "module"

    def test_ignores_invalid_demo_prompts(self) -> None:
        mod = _make_module({"DEMO_PROMPTS": [{"no_content": True}]})
        config = _make_config()
        loader = DemoLoader()
        prompts = loader._find_prompts(mod, config)
        # The dict without 'content' key is skipped; falls through to source extraction
        assert all(p.source in ("module", "source") for p in prompts)


# MARK: _find_invocation_config


class TestFindInvocationConfig:
    def test_valid_config(self) -> None:
        mod = _make_module(
            {
                "DEMO_INVOCATION": {
                    "model": "gpt-4",
                    "reasoning": True,
                    "force_final_tool": "my_tool",
                    "garbage_key": "ignored",
                }
            }
        )
        loader = DemoLoader()
        result = loader._find_invocation_config(mod)

        assert result is not None
        assert result["model"] == "gpt-4"
        assert result["reasoning"] is True
        assert result["force_final_tool"] == "my_tool"
        assert "garbage_key" not in result

    def test_returns_none_for_non_dict(self) -> None:
        mod = _make_module({"DEMO_INVOCATION": "not a dict"})
        loader = DemoLoader()
        assert loader._find_invocation_config(mod) is None

    def test_returns_none_when_missing(self) -> None:
        mod = _make_module()
        loader = DemoLoader()
        assert loader._find_invocation_config(mod) is None


# MARK: _find_executor_name


class TestFindExecutorName:
    def test_valid_string(self) -> None:
        mod = _make_module({"DEMO_EXECUTOR": "my_agent"})
        loader = DemoLoader()
        assert loader._find_executor_name(mod) == "my_agent"

    def test_returns_none_for_non_string(self) -> None:
        mod = _make_module({"DEMO_EXECUTOR": 123})
        loader = DemoLoader()
        assert loader._find_executor_name(mod) is None

    def test_returns_none_when_missing(self) -> None:
        mod = _make_module()
        loader = DemoLoader()
        assert loader._find_executor_name(mod) is None

    def test_returns_none_for_blank_string(self) -> None:
        mod = _make_module({"DEMO_EXECUTOR": "   "})
        loader = DemoLoader()
        assert loader._find_executor_name(mod) is None


# MARK: load


class TestLoad:
    def test_load_imports_module(self) -> None:
        agent = _mock_agent("a1")
        fake_mod = _make_module({"a1": agent})
        config = _make_config(module="some.module")
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=fake_mod) as mock_import:
            loaded = loader.load(config)

        mock_import.assert_called_once_with("some.module")
        assert loaded.agents == [agent]
        assert loaded.config is config

    def test_load_caches_result(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            first = loader.load(config)
            second = loader.load(config)

        assert first is second

    def test_load_force_reload(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = DemoLoader()

        with patch("maivn_studio.services.demo_loader.loader.importlib") as mock_importlib:
            mock_importlib.import_module.return_value = fake_mod
            mock_importlib.reload.return_value = fake_mod
            loader.load(config)
            loader.load(config, force_reload=True)

        assert mock_importlib.import_module.call_count == 2
        mock_importlib.reload.assert_called_once_with(fake_mod)

    def test_load_with_variant_cache_key(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loader.load(config, variant="v1")
            loader.load(config, variant="v2")

        # Different variants get different cache entries
        assert "test-demo:v1" in loader._cache
        assert "test-demo:v2" in loader._cache

    def test_load_raises_import_error(self) -> None:
        config = _make_config(module="nonexistent.module")
        loader = DemoLoader()

        with patch("importlib.import_module", side_effect=ImportError("not found")):
            with pytest.raises(ImportError, match="not found"):
                loader.load(config)

    def test_load_variant_rebuilds_prompts_after_configure_variant(self) -> None:
        module = _make_module(
            {
                "DEMO_PROMPTS": [{"name": "Default", "content": "generic prompt"}],
            }
        )

        def _configure_variant(variant: str | None) -> None:
            if variant == "with-private-data":
                module.DEMO_PROMPTS = [
                    {
                        "name": "Private Prompt",
                        "content": "email studio-think-private@maivn.dev",
                    }
                ]
            else:
                module.DEMO_PROMPTS = [{"name": "Default", "content": "generic prompt"}]

        module.configure_variant = _configure_variant

        config = _make_config()
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=module):
            loaded = loader.load(config, variant="with-private-data")

        assert len(loaded.prompts) == 1
        assert loaded.prompts[0].content == "email studio-think-private@maivn.dev"


# MARK: get and unload


class TestGetAndUnload:
    def test_get_returns_cached(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loaded = loader.load(config)

        assert loader.get("test-demo") is loaded

    def test_get_returns_none_for_missing(self) -> None:
        loader = DemoLoader()
        assert loader.get("nonexistent") is None

    def test_unload_removes_from_cache(self) -> None:
        fake_mod = _make_module()
        config = _make_config()
        loader = DemoLoader()

        with patch("importlib.import_module", return_value=fake_mod):
            loader.load(config)
            loader.load(config, variant="v1")

        assert loader.get("test-demo") is not None
        loader.unload("test-demo")
        assert loader.get("test-demo") is None
        # Variant entries with prefix also removed
        assert "test-demo:v1" not in loader._cache


# MARK: _apply_variant


class TestApplyVariant:
    def test_calls_configure_variant(self) -> None:
        mock_fn = MagicMock()
        mod = _make_module({"configure_variant": mock_fn})
        loader = DemoLoader()
        loader._apply_variant(mod, "v1")
        mock_fn.assert_called_once_with("v1")

    def test_noop_without_configure_variant(self) -> None:
        mod = _make_module()
        loader = DemoLoader()
        # Should not raise
        loader._apply_variant(mod, "v1")

    def test_handles_exception_gracefully(self) -> None:
        mock_fn = MagicMock(side_effect=ValueError("boom"))
        mod = _make_module({"configure_variant": mock_fn})
        loader = DemoLoader()
        # Should not raise, just log warning
        loader._apply_variant(mod, "v1")


# MARK: LoadedDemo.executor


class TestLoadedDemoExecutor:
    def test_prefers_explicit_executor(self) -> None:
        agent = _mock_agent("target")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(
            config=config,
            module=mod,
            agents=[agent],
            explicit_executor_name="target",
        )
        assert loaded.executor is agent

    def test_falls_back_to_swarm(self) -> None:
        swarm = _mock_swarm("s1")
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[agent], swarms=[swarm])
        assert loaded.executor is swarm

    def test_falls_back_to_agent(self) -> None:
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[agent])
        assert loaded.executor is agent

    def test_returns_none_when_empty(self) -> None:
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod)
        assert loaded.executor is None


# MARK: LoadedDemo.executor_type


class TestLoadedDemoExecutorType:
    def test_swarm_type(self) -> None:
        swarm = _mock_swarm("s1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, swarms=[swarm])
        assert loaded.executor_type == "swarm"

    def test_agent_type(self) -> None:
        agent = _mock_agent("a1")
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[agent])
        assert loaded.executor_type == "agent"

    def test_none_type(self) -> None:
        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod)
        assert loaded.executor_type == "none"


# MARK: LoadedDemo.get_tools


class TestLoadedDemoGetTools:
    def test_collects_tools_from_agents(self) -> None:
        tool_mock = MagicMock()
        tool_mock.name = "my_tool"
        tool_mock.description = "A tool"
        tool_mock.final_tool = False

        repo_mock = MagicMock()
        repo_mock.list_tools.return_value = [tool_mock]

        agent = _mock_agent("a1")
        agent._tool_repo = repo_mock

        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[agent])
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
        a1._tool_repo = repo
        a2 = _mock_agent("a2")
        a2._tool_repo = repo

        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[a1, a2])
        tools = loaded.get_tools()
        assert len(tools) == 1

    def test_returns_empty_without_tool_repo(self) -> None:
        agent = _mock_agent("a1")

        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[agent])
        assert loaded.get_tools() == []


# MARK: LoadedDemo.get_all_agents


class TestLoadedDemoGetAllAgents:
    def test_includes_standalone_and_swarm_agents(self) -> None:
        standalone = _mock_agent("standalone", description="Solo")
        member = _mock_agent("member", description="In swarm")
        swarm = _mock_swarm("s1", agents=[member])

        config = _make_config()
        mod = _make_module()
        loaded = LoadedDemo(config=config, module=mod, agents=[standalone], swarms=[swarm])
        result = loaded.get_all_agents()

        assert len(result) == 2
        assert result[0]["name"] == "standalone"
        assert result[0]["is_swarm_member"] is False
        assert result[1]["name"] == "member"
        assert result[1]["is_swarm_member"] is True
        assert result[1]["swarm"] == "s1"
