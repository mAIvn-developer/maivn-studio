"""Tests for introspection helpers in api/routes/apps/introspection.py."""

from __future__ import annotations

from typing import Any

from maivn import Agent
from maivn_shared import DataDependency, MemoryConfig
from pydantic import BaseModel

from maivn_studio.api.routes.apps.introspection import (
    build_agent_info,
    build_swarm_info,
    build_tool_info,
    collect_private_data_keys,
    extract_system_prompt,
    normalize_included_nested_synthesis,
)

# MARK: extract_system_prompt


class TestExtractSystemPrompt:
    def test_string_prompt(self) -> None:
        class Scope:
            system_prompt = "You are a helper."

        assert extract_system_prompt(Scope()) == "You are a helper."

    def test_none_prompt(self) -> None:
        class Scope:
            system_prompt = None

        assert extract_system_prompt(Scope()) is None

    def test_missing_attr(self) -> None:
        class Scope:
            pass

        assert extract_system_prompt(Scope()) is None

    def test_system_message_object(self) -> None:
        class FakeMessage:
            content = "System message content"

        class Scope:
            system_prompt = FakeMessage()

        assert extract_system_prompt(Scope()) == "System message content"

    def test_object_without_content(self) -> None:
        """Falls back to str() when no .content attr."""

        class Obj:
            def __str__(self) -> str:
                return "stringified"

        class Scope:
            system_prompt = Obj()

        assert extract_system_prompt(Scope()) == "stringified"


# MARK: collect_private_data_keys


class TestCollectPrivateDataKeys:
    def test_with_data_dependencies(self) -> None:
        class Tool:
            dependencies = [
                DataDependency(data_key="api_key", arg_name="key"),
                DataDependency(data_key="secret", arg_name="sec"),
            ]

        class Scope:
            def list_tools(self) -> list:
                return [Tool()]

        keys = collect_private_data_keys(Scope())
        assert keys == ["api_key", "secret"]

    def test_empty_tools(self) -> None:
        class Scope:
            def list_tools(self) -> list:
                return []

        assert collect_private_data_keys(Scope()) == []

    def test_exception_in_list_tools(self) -> None:
        class Scope:
            def list_tools(self) -> list:
                raise RuntimeError("boom")

        assert collect_private_data_keys(Scope()) == []

    def test_no_dependencies_attr(self) -> None:
        class Tool:
            pass

        class Scope:
            def list_tools(self) -> list:
                return [Tool()]

        assert collect_private_data_keys(Scope()) == []

    def test_none_dependencies(self) -> None:
        class Tool:
            dependencies = None

        class Scope:
            def list_tools(self) -> list:
                return [Tool()]

        assert collect_private_data_keys(Scope()) == []

    def test_deduplicates_keys(self) -> None:
        class Tool:
            dependencies = [
                DataDependency(data_key="same_key", arg_name="a"),
                DataDependency(data_key="same_key", arg_name="b"),
            ]

        class Scope:
            def list_tools(self) -> list:
                return [Tool()]

        assert collect_private_data_keys(Scope()) == ["same_key"]

    def test_dep_without_data_key(self) -> None:
        """DataDependency with data_key=None should be skipped."""

        class NonDataDep:
            data_key = None

        class Tool:
            dependencies = [NonDataDep()]

        class Scope:
            def list_tools(self) -> list:
                return [Tool()]

        assert collect_private_data_keys(Scope()) == []


# MARK: normalize_included_nested_synthesis


class TestNormalizeIncludedNestedSynthesis:
    def test_bool_true(self) -> None:
        assert normalize_included_nested_synthesis(True) is True

    def test_bool_false(self) -> None:
        assert normalize_included_nested_synthesis(False) is False

    def test_string_auto(self) -> None:
        assert normalize_included_nested_synthesis("auto") == "auto"

    def test_string_auto_uppercase(self) -> None:
        assert normalize_included_nested_synthesis("AUTO") == "auto"

    def test_string_true_variants(self) -> None:
        for val in ["true", "True", "1", "yes", "on", " YES "]:
            assert normalize_included_nested_synthesis(val) is True, f"Failed for {val!r}"

    def test_string_false_variants(self) -> None:
        for val in ["false", "False", "0", "no", "off", " NO "]:
            assert normalize_included_nested_synthesis(val) is False, f"Failed for {val!r}"

    def test_unknown_string(self) -> None:
        assert normalize_included_nested_synthesis("maybe") == "auto"

    def test_non_string_non_bool(self) -> None:
        assert normalize_included_nested_synthesis(42) == "auto"
        assert normalize_included_nested_synthesis(None) == "auto"


# MARK: build_agent_info


class TestBuildAgentInfo:
    def _make_agent(self, **overrides: Any) -> Any:
        class Agent:
            name = "test_agent"
            description = "Test agent"
            system_prompt = "Be helpful."
            tags = ["tag1"]
            memory_config = MemoryConfig()
            private_data = {"key": "val"}
            timeout = 10.0
            max_results = 5
            use_as_final_output = False
            included_nested_synthesis = "auto"
            allow_private_in_system_tools = False
            hook_execution_mode = "tool"
            before_execute = None
            after_execute = None

            def list_tools(self) -> list:
                return []

            def list_mcp_servers(self) -> list:
                return []

        agent = Agent()
        for k, v in overrides.items():
            setattr(agent, k, v)
        return agent

    def test_basic_agent_info(self) -> None:
        agent = self._make_agent()
        info = build_agent_info(agent, "test_agent", {})
        assert info.name == "test_agent"
        assert info.description == "Test agent"
        assert info.system_prompt == "Be helpful."
        assert info.tags == ["tag1"]
        assert info.timeout == 10.0
        assert info.max_results == 5
        assert info.is_swarm_member is False
        assert info.swarm is None

    def test_swarm_membership(self) -> None:
        agent = self._make_agent()
        info = build_agent_info(agent, "test_agent", {"test_agent": "my_swarm"})
        assert info.is_swarm_member is True
        assert info.swarm == "my_swarm"

    def test_mcp_servers(self) -> None:
        class MCPServer:
            name = "mcp-test"

        agent = self._make_agent()
        agent.list_mcp_servers = lambda: [MCPServer()]
        info = build_agent_info(agent, "test_agent", {})
        assert info.mcp_server_names == ["mcp-test"]

    def test_mcp_servers_exception(self) -> None:
        agent = self._make_agent()
        agent.list_mcp_servers = lambda: (_ for _ in ()).throw(RuntimeError("fail"))
        info = build_agent_info(agent, "test_agent", {})
        assert info.mcp_server_names == []

    def test_hooks_detected(self) -> None:
        agent = self._make_agent(before_execute=lambda: None, after_execute=lambda: None)
        info = build_agent_info(agent, "test_agent", {})
        assert info.has_before_hook is True
        assert info.has_after_hook is True

    def test_tool_count(self) -> None:
        class Tool:
            pass

        agent = self._make_agent()
        agent.list_tools = lambda: [Tool(), Tool(), Tool()]
        info = build_agent_info(agent, "test_agent", {})
        assert info.tool_count == 3
        assert info.runtime_tool_count == 3

    def test_tool_count_exception(self) -> None:
        agent = self._make_agent()
        agent.list_tools = lambda: (_ for _ in ()).throw(RuntimeError("fail"))
        info = build_agent_info(agent, "test_agent", {})
        assert info.tool_count == 0
        assert info.runtime_tool_count == 0

    def test_runtime_tool_count_flattens_nested_model_tools(self) -> None:
        agent = Agent(name="nested_agent", api_key="test-api-key")

        class Sensor(BaseModel):
            resolution: str

        @agent.toolify(description="Nested robot schema")
        class Robot(BaseModel):
            sensor: Sensor

        info = build_agent_info(agent, "nested_agent", {})
        assert info.tool_count == 1
        assert info.runtime_tool_count == 2


# MARK: build_swarm_info


class TestBuildSwarmInfo:
    def _make_swarm(self, agent_count: int = 1, tools_per_agent: int = 2) -> Any:
        class Tool:
            pass

        class Agent:
            def __init__(self, name: str) -> None:
                self.name = name

            def list_tools(self) -> list:
                return [Tool() for _ in range(tools_per_agent)]

        class Swarm:
            name = "test_swarm"
            description = "Test swarm"
            system_prompt = "Swarm prompt"
            tags = ["swarm-tag"]
            memory_config = MemoryConfig()
            allow_private_in_system_tools = False
            private_data = {}

            def __init__(self) -> None:
                self.agents = [Agent(f"agent_{i}") for i in range(agent_count)]

            def list_tools(self) -> list:
                return []

        return Swarm()

    def test_basic_swarm(self) -> None:
        swarm = self._make_swarm(agent_count=2, tools_per_agent=3)
        info = build_swarm_info(swarm)
        assert info.name == "test_swarm"
        assert info.description == "Test swarm"
        assert info.system_prompt == "Swarm prompt"
        assert info.agent_count == 2
        assert info.agent_names == ["agent_0", "agent_1"]
        assert info.tool_count == 6  # 2 agents * 3 tools each
        assert info.runtime_tool_count == 6

    def test_swarm_no_agents(self) -> None:
        class Swarm:
            name = "empty_swarm"
            description = ""
            system_prompt = None
            tags = []
            memory_config = MemoryConfig()
            allow_private_in_system_tools = False
            private_data = {}

            def list_tools(self) -> list:
                return []

        swarm = Swarm()
        # No agents attribute
        info = build_swarm_info(swarm)
        assert info.agent_count == 0
        assert info.tool_count == 0
        assert info.runtime_tool_count == 0

    def test_swarm_agent_tool_exception(self) -> None:
        class BrokenAgent:
            name = "broken"

            def list_tools(self) -> list:
                raise RuntimeError("tools broken")

        class Swarm:
            name = "swarm_with_broken"
            description = ""
            system_prompt = None
            tags = []
            memory_config = MemoryConfig()
            allow_private_in_system_tools = False
            private_data = {}

            def __init__(self) -> None:
                self.agents = [BrokenAgent()]

            def list_tools(self) -> list:
                return []

        info = build_swarm_info(Swarm())
        assert info.agent_count == 1
        assert info.tool_count == 0  # Exception caught gracefully
        assert info.runtime_tool_count == 0


# MARK: build_tool_info


class TestBuildToolInfo:
    def test_basic_tool(self) -> None:
        class Tool:
            name = "my_tool"
            description = "A tool"
            tool_type = "func"
            final_tool = False
            always_execute = True
            tags = ["t1"]
            dependencies = []
            args_schema = None

        info = build_tool_info(Tool(), "agent1")
        assert info.name == "my_tool"
        assert info.description == "A tool"
        assert info.agent == "agent1"
        assert info.tool_type == "func"
        assert info.always_execute is True
        assert info.dependencies == []
        assert info.args_schema is None

    def test_tool_with_dependencies(self) -> None:
        class Dep:
            name = "dep1"
            dependency_type = "data"
            arg_name = "arg1"
            data_key = "key1"
            tool_id = None
            agent_id = None
            prompt = None
            input_type = None

        class Tool:
            name = "tool_with_deps"
            description = ""
            tool_type = "func"
            final_tool = False
            always_execute = False
            tags = []
            dependencies = [Dep()]
            args_schema = None

        info = build_tool_info(Tool(), "agent1")
        assert len(info.dependencies) == 1
        assert info.dependencies[0].name == "dep1"
        assert info.dependencies[0].dependency_type == "data"
        assert info.dependencies[0].data_key == "key1"

    def test_tool_with_dict_args_schema(self) -> None:
        schema = {"type": "object", "properties": {"x": {"type": "string"}}}

        class Tool:
            name = "schema_tool"
            description = ""
            tool_type = "func"
            final_tool = False
            always_execute = False
            tags = []
            dependencies = []
            args_schema = schema

        info = build_tool_info(Tool(), "agent1")
        assert info.args_schema == schema

    def test_tool_with_pydantic_args_schema(self) -> None:
        from pydantic import BaseModel

        class MySchema(BaseModel):
            x: str
            y: int = 0

        class Tool:
            name = "pydantic_tool"
            description = ""
            tool_type = "func"
            final_tool = False
            always_execute = False
            tags = []
            dependencies = []
            args_schema = MySchema

        info = build_tool_info(Tool(), "agent1")
        assert info.args_schema is not None
        assert "properties" in info.args_schema

    def test_tool_with_broken_pydantic_schema(self) -> None:
        class BrokenSchema:
            def model_json_schema(self) -> dict:
                raise TypeError("broken")

        class Tool:
            name = "broken_tool"
            description = ""
            tool_type = "func"
            final_tool = False
            always_execute = False
            tags = []
            dependencies = []
            args_schema = BrokenSchema()

        info = build_tool_info(Tool(), "agent1")
        assert info.args_schema is None

    def test_tool_with_enum_tool_type(self) -> None:
        from enum import Enum

        class ToolType(str, Enum):
            FUNC = "func"
            MODEL = "model"

        class Tool:
            name = "enum_tool"
            description = ""
            tool_type = ToolType.FUNC
            final_tool = True
            always_execute = False
            tags = []
            dependencies = None
            args_schema = None

        info = build_tool_info(Tool(), "agent1")
        assert info.tool_type == "func"
        assert info.final_tool is True

    def test_tool_none_dependencies(self) -> None:
        class Tool:
            name = "no_deps"
            description = ""
            tool_type = "func"
            final_tool = False
            always_execute = False
            tags = None
            dependencies = None
            args_schema = None

        info = build_tool_info(Tool(), "agent1")
        assert info.dependencies == []
        assert info.tags == []
