"""Introspection helpers for extracting info from live SDK objects."""

# pyright: strict

from __future__ import annotations

from typing import Any, Literal, Protocol, cast

from maivn_shared import MemoryConfig, SessionOrchestrationConfig, SystemToolsConfig

from maivn_studio.config.models import AppConfig

from .models import (
    AgentInfo,
    AppSummary,
    DependencyInfo,
    SwarmInfo,
    ToolInfo,
)

# MARK: Types


class _ToolSpecLike(Protocol):
    """Minimal studio-side view of an SDK ``ToolSpec`` (which exposes ``tool_id``).

    Used to tighten the ``maivn._internal.core.tool_specs`` boundary, whose stubs
    are not reachable to the type checker.
    """

    @property
    def tool_id(self) -> str: ...


class _HasModelJsonSchema(Protocol):
    """A Pydantic-like object exposing ``model_json_schema``."""

    def model_json_schema(self) -> dict[str, Any]: ...


# MARK: App Summary


def build_app_summary(
    app: AppConfig,
    source: Literal["configured", "discovered"],
) -> AppSummary:
    """Convert an AppConfig plus registry source metadata into API summary model."""
    return AppSummary(
        id=app.id,
        name=app.name,
        description=app.description,
        module=app.module,
        category=app.category,
        tags=list(app.tags),
        variants=app.variants,
        private_data=app.private_data,
        source=source,
    )


# MARK: System Prompt Extraction


def extract_system_prompt(scope: Any) -> str | None:
    """Extract system prompt text from a scope (Agent or Swarm)."""
    sp = getattr(scope, "system_prompt", None)
    if sp is None:
        return None
    if isinstance(sp, str):
        return sp
    # SystemMessage object
    content = getattr(sp, "content", None)
    if content is not None:
        return str(content)
    return str(sp)


# MARK: Private Data Keys


def collect_private_data_keys(scope: Any) -> list[str]:
    """Collect private_data keys required by a scope's tools."""
    from maivn_shared import DataDependency

    keys: set[str] = set()
    try:
        tools = scope.list_tools()
    except Exception:  # noqa: BLE001 - introspection of live SDK objects; any failure means "no keys"
        return []
    for tool in tools:
        for dep in getattr(tool, "dependencies", []) or []:
            if isinstance(dep, DataDependency) and dep.data_key:
                keys.add(dep.data_key)
    return sorted(keys)


def collect_runtime_tool_count(scope: Any) -> int:
    """Count flattened runtime ToolSpecs for a scope.

    Studio's live object introspection only sees authored SDK tools. Runtime
    execution expands nested ModelTool schemas into additional ToolSpecs, so we
    expose that flattened count separately for UI summaries.
    """
    try:
        tools = list(scope.list_tools())
    except Exception:  # noqa: BLE001 - tool listing can fail on partially-initialized scopes
        return 0

    if not tools:
        return 0

    try:
        from maivn._internal.core.tool_specs import (
            ToolSpecFactory,
        )

        factory = ToolSpecFactory()
        agent_id = getattr(scope, "id", None) or getattr(scope, "agent_id", "") or ""
        tool_ids: set[str] = set()
        for tool in tools:
            specs = cast(
                "list[_ToolSpecLike]",
                factory.create_all(
                    agent_id=str(agent_id),
                    tool=tool,
                    dependencies=getattr(tool, "dependencies", None),
                    always_execute=getattr(tool, "always_execute", False),
                    final_tool=getattr(tool, "final_tool", False),
                ),
            )
            tool_ids.update(spec.tool_id for spec in specs)
        return len(tool_ids)
    except Exception:  # noqa: BLE001 - ToolSpec expansion is best-effort; fall back to authored count
        return len(tools)


# MARK: Agent Info


def build_agent_info(
    agent: Any,
    agent_name: str,
    swarm_agents: dict[str, str],
) -> AgentInfo:
    """Build an AgentInfo from a live Agent instance."""
    tool_count = 0
    try:
        tool_count = len(agent.list_tools())
    except Exception:  # noqa: BLE001 - missing tool list is non-fatal for the summary card
        pass
    runtime_tool_count = collect_runtime_tool_count(agent)

    mcp_names: list[str] = []
    try:
        for srv in agent.list_mcp_servers():
            mcp_names.append(getattr(srv, "name", str(srv)))
    except Exception:  # noqa: BLE001 - MCP discovery may fail before server is reachable
        pass

    return AgentInfo(
        name=agent_name,
        description=getattr(agent, "description", "") or "",
        system_prompt=extract_system_prompt(agent),
        tags=list(getattr(agent, "tags", []) or []),
        memory_config=getattr(agent, "memory_config", MemoryConfig()),
        system_tools_config=getattr(agent, "system_tools_config", SystemToolsConfig()),
        orchestration_config=getattr(
            agent,
            "orchestration_config",
            SessionOrchestrationConfig(),
        ),
        private_data=dict(getattr(agent, "private_data", {}) or {}),
        tool_count=tool_count,
        runtime_tool_count=runtime_tool_count,
        timeout=getattr(agent, "timeout", None),
        max_results=getattr(agent, "max_results", None),
        use_as_final_output=getattr(agent, "use_as_final_output", False),
        included_nested_synthesis=normalize_included_nested_synthesis(
            getattr(agent, "included_nested_synthesis", "auto")
        ),
        allow_private_in_system_tools=getattr(agent, "allow_private_in_system_tools", False),
        hook_execution_mode=getattr(agent, "hook_execution_mode", "tool"),
        has_before_hook=getattr(agent, "before_execute", None) is not None,
        has_after_hook=getattr(agent, "after_execute", None) is not None,
        mcp_server_names=mcp_names,
        private_data_keys=collect_private_data_keys(agent),
        is_swarm_member=agent_name in swarm_agents,
        swarm=swarm_agents.get(agent_name),
    )


# MARK: Nested Synthesis Normalization


def normalize_included_nested_synthesis(value: Any) -> bool | Literal["auto"]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "auto":
            return "auto"
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False
    return "auto"


# MARK: Swarm Info


def build_swarm_info(swarm: Any) -> SwarmInfo:
    """Build a SwarmInfo from a live Swarm instance."""
    swarm_name = getattr(swarm, "name", str(swarm))
    agent_names: list[str] = []
    total_tools = 0
    runtime_total_tools = 0

    if hasattr(swarm, "agents"):
        for agent in swarm.agents:
            agent_names.append(getattr(agent, "name", str(agent)))
            try:
                total_tools += len(agent.list_tools())
            except Exception:  # noqa: BLE001 - per-agent tool count is best-effort for the summary
                pass
            runtime_total_tools += collect_runtime_tool_count(agent)

    return SwarmInfo(
        name=swarm_name,
        description=getattr(swarm, "description", "") or "",
        system_prompt=extract_system_prompt(swarm),
        tags=list(getattr(swarm, "tags", []) or []),
        memory_config=getattr(swarm, "memory_config", MemoryConfig()),
        system_tools_config=getattr(swarm, "system_tools_config", SystemToolsConfig()),
        orchestration_config=getattr(
            swarm,
            "orchestration_config",
            SessionOrchestrationConfig(),
        ),
        allow_private_in_system_tools=getattr(swarm, "allow_private_in_system_tools", False),
        private_data=dict(getattr(swarm, "private_data", {}) or {}),
        agent_count=len(agent_names),
        agent_names=agent_names,
        tool_count=total_tools,
        runtime_tool_count=runtime_total_tools,
        private_data_keys=collect_private_data_keys(swarm),
    )


# MARK: Tool Info


def build_tool_info(tool: Any, agent_name: str) -> ToolInfo:
    """Build a ToolInfo from a live BaseTool instance."""
    tool_name = getattr(tool, "name", str(tool))
    tool_desc = getattr(tool, "description", "") or ""
    raw_tool_type = getattr(tool, "tool_type", "func")
    tool_type = getattr(raw_tool_type, "value", raw_tool_type)

    # Build dependency list
    deps: list[DependencyInfo] = []
    for dep in getattr(tool, "dependencies", []) or []:
        deps.append(
            DependencyInfo(
                name=getattr(dep, "name", ""),
                dependency_type=getattr(dep, "dependency_type", "unknown"),
                arg_name=getattr(dep, "arg_name", ""),
                data_key=getattr(dep, "data_key", None),
                tool_id=getattr(dep, "tool_id", None),
                agent_id=getattr(dep, "agent_id", None),
                prompt=getattr(dep, "prompt", None),
                input_type=getattr(dep, "input_type", None),
            )
        )

    # Extract args schema
    args_schema: dict[str, Any] | None = None
    raw_schema: object = getattr(tool, "args_schema", None)
    if isinstance(raw_schema, dict):
        args_schema = cast("dict[str, Any]", raw_schema)
    elif raw_schema is not None and hasattr(raw_schema, "model_json_schema"):
        try:
            args_schema = cast("_HasModelJsonSchema", raw_schema).model_json_schema()
        except Exception:  # noqa: BLE001 - Pydantic schema dump can fail on dynamic models; omit
            pass

    return ToolInfo(
        name=tool_name,
        description=tool_desc,
        agent=agent_name,
        tool_type=str(tool_type),
        final_tool=getattr(tool, "final_tool", False),
        always_execute=getattr(tool, "always_execute", False),
        tags=list(getattr(tool, "tags", []) or []),
        dependencies=deps,
        args_schema=args_schema,
    )
