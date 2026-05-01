"""API route handlers for demo management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

from maivn_studio.config.models import DemoConfig, PrivateDataField
from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.demo_loader.loader import get_demo_loader

from .introspection import build_agent_info, build_demo_summary, build_swarm_info, build_tool_info
from .models import (
    AgentInfo,
    DemoDetailResponse,
    DemoFullDetailsResponse,
    DemoListResponse,
    PromptInfo,
    SwarmInfo,
    ToolInfo,
    UpdateAgentRequest,
    UpdateDemoRequest,
    UpdateSwarmRequest,
)

router = APIRouter(prefix="/api/demos", tags=["demos"])
logger = logging.getLogger(__name__)


# MARK: Helpers


def calculate_demo_runtime_tool_count(agents: list[AgentInfo], swarms: list[SwarmInfo]) -> int:
    """Count demo runtime tools without double-counting swarm member agents."""
    standalone_agent_tools = sum(
        agent.runtime_tool_count for agent in agents if not agent.is_swarm_member
    )
    swarm_tools = sum(swarm.runtime_tool_count for swarm in swarms)
    return standalone_agent_tools + swarm_tools


def _resolve_demo_variant(demo: DemoConfig, requested_variant: str | None = None) -> str | None:
    """Resolve the effective variant for a demo, honoring configured defaults."""
    variant = requested_variant or demo.default_variant
    if not variant:
        return None
    if variant in demo.variants:
        return variant

    logger.warning(
        "Ignoring invalid default variant %r for demo %s; available variants: %s",
        variant,
        demo.id,
        sorted(demo.variants.keys()),
    )
    return None


def _build_private_data_defaults(
    demo: DemoConfig, resolved_variant: str | None
) -> dict[str, str | int | bool]:
    """Build the effective private data defaults for a demo details view."""
    defaults = dict(demo.private_data)
    if resolved_variant:
        defaults.update(demo.variants[resolved_variant].private_data)
    return defaults


def _infer_private_data_type(value: str | int | bool) -> str:
    """Infer the Studio field type for a configured private data value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    return "string"


def _merge_private_data_schema(
    schema: list[PrivateDataField], defaults: dict[str, str | int | bool]
) -> list[PrivateDataField]:
    """Overlay configured defaults onto extracted schema and add missing keys."""
    merged: list[PrivateDataField] = []
    schema_by_key = {field.key: field for field in schema}

    for field in schema:
        configured_default = defaults.get(field.key, field.default_value)
        resolved_type = field.type
        if not resolved_type:
            resolved_type = (
                _infer_private_data_type(configured_default)
                if configured_default is not None
                else "string"
            )
        merged.append(
            field.model_copy(
                update={
                    "default_value": configured_default,
                    "type": resolved_type,
                }
            )
        )

    for key in sorted(defaults):
        if key in schema_by_key:
            continue
        default_value = defaults[key]
        merged.append(
            PrivateDataField(
                key=key,
                label=key.replace("_", " ").title(),
                type=_infer_private_data_type(default_value),
                required=False,
                default_value=default_value,
                description=f"Configured private data value for {key}",
            )
        )

    return merged


# MARK: Read Routes


@router.get("", response_model=DemoListResponse)
async def list_demos(category: str | None = None) -> DemoListResponse:
    """List all available demos.

    Args:
        category: Optional category filter.

    Returns:
        List of demos with metadata.
    """
    registry = get_registry()

    if category:
        demos = registry.get_by_category(category)
    else:
        demos = registry.demos

    demo_summaries = [build_demo_summary(demo, registry.get_source(demo.id)) for demo in demos]

    return DemoListResponse(
        demos=demo_summaries,
        total=len(demos),
        categories=registry.categories,
    )


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """List all demo categories.

    Returns:
        List of category names.
    """
    registry = get_registry()
    return registry.categories


@router.get("/{demo_id}", response_model=DemoDetailResponse)
async def get_demo(demo_id: str) -> DemoDetailResponse:
    """Get details for a specific demo.

    Args:
        demo_id: The demo ID.

    Returns:
        Demo details including variants.

    Raises:
        HTTPException: If demo not found.
    """
    registry = get_registry()
    demo = registry.get(demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {demo_id}")

    return DemoDetailResponse(
        demo=build_demo_summary(demo, registry.get_source(demo_id)),
        variants=demo.variants,
    )


@router.get("/{demo_id}/details", response_model=DemoFullDetailsResponse)
async def get_demo_full_details(
    demo_id: str, variant: str | None = None
) -> DemoFullDetailsResponse:
    """Get full details for a demo including private data schema.

    Args:
        demo_id: The demo ID.
        variant: Optional demo variant to load.

    Returns:
        Full demo details.

    Raises:
        HTTPException: If demo not found.
    """
    registry = get_registry()
    demo = registry.get(demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {demo_id}")

    # Load the demo to get full details
    loader = get_demo_loader()
    resolved_variant = _resolve_demo_variant(demo, variant)
    loaded = loader.load(demo, variant=resolved_variant)

    # Build agents list
    agents: list[AgentInfo] = []
    swarm_agents: dict[str, str] = {}  # agent_name -> swarm_name

    # Track which agents are in swarms
    for swarm in loaded.swarms:
        if hasattr(swarm, "agents"):
            for agent in swarm.agents:
                swarm_agents[getattr(agent, "name", str(agent))] = getattr(
                    swarm, "name", str(swarm)
                )

    for agent in loaded.agents:
        agent_name = getattr(agent, "name", str(agent))
        agents.append(build_agent_info(agent, agent_name, swarm_agents))

    # Build swarms list
    swarms: list[SwarmInfo] = []
    for swarm in loaded.swarms:
        swarms.append(build_swarm_info(swarm))

    # Build tools list
    tools: list[ToolInfo] = []
    for agent in loaded.agents:
        agent_name = getattr(agent, "name", str(agent))
        try:
            agent_tools = agent.list_tools()
            for tool in agent_tools:
                tools.append(build_tool_info(tool, agent_name))
        except Exception:
            pass

    # Build prompts list
    prompts: list[PromptInfo] = []
    for i, prompt in enumerate(loaded.prompts):
        prompt_name = getattr(prompt, "name", "")
        prompt_content = getattr(prompt, "content", "")
        prompt_description = getattr(prompt, "description", "")
        prompt_source = getattr(prompt, "source", "discovered")
        prompt_is_default = getattr(prompt, "is_default", i == 0)
        prompt_structured_output = getattr(prompt, "structured_output", None)
        prompt_message_type = getattr(prompt, "message_type", None)
        prompt_variant = getattr(prompt, "variant", None)
        if prompt_variant and prompt_variant not in demo.variants:
            logger.warning(
                "Ignoring invalid prompt variant %r for demo %s prompt %r; available variants: %s",
                prompt_variant,
                demo_id,
                prompt_name or f"Prompt {i + 1}",
                sorted(demo.variants.keys()),
            )
            prompt_variant = None
        prompts.append(
            PromptInfo(
                id=f"{demo_id}-prompt-{i}",
                name=prompt_name or f"Prompt {i + 1}",
                content=prompt_content,
                description=prompt_description,
                is_default=prompt_is_default,
                source=prompt_source,
                structured_output=prompt_structured_output,
                message_type=prompt_message_type,
                variant=prompt_variant,
            )
        )

    # Extract private data schema
    from maivn_studio.private_data import extract_private_data_schema

    private_data_defaults = _build_private_data_defaults(demo, resolved_variant)
    private_data_schema = _merge_private_data_schema(
        extract_private_data_schema(loaded),
        private_data_defaults,
    )

    return DemoFullDetailsResponse(
        id=demo.id,
        name=demo.name,
        description=demo.description,
        module=demo.module,
        category=demo.category,
        tags=demo.tags,
        variants=demo.variants,
        source=registry.get_source(demo_id),
        agents=agents,
        swarms=swarms,
        tools=tools,
        prompts=prompts,
        privateDataSchema=private_data_schema,
        privateDataDefaults=private_data_defaults,
        defaultInvocation=loaded.default_invocation,
        runtime_tool_count=calculate_demo_runtime_tool_count(agents, swarms),
    )


# MARK: Update Routes


@router.patch("/{demo_id}", response_model=DemoDetailResponse)
async def update_demo(demo_id: str, request: UpdateDemoRequest) -> DemoDetailResponse:
    """Update a demo's configuration.

    Args:
        demo_id: The demo ID.
        request: Fields to update.

    Returns:
        Updated demo details.

    Raises:
        HTTPException: If demo not found.
    """
    from maivn_studio.config.loader import get_config, save_config

    registry = get_registry()
    demo = registry.get(demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {demo_id}")

    # Apply updates to in-memory config
    if request.name is not None:
        demo.name = request.name
    if request.description is not None:
        demo.description = request.description
    if request.category is not None:
        demo.category = request.category
    if request.tags is not None:
        demo.tags = request.tags
    if request.variants is not None:
        demo.variants = request.variants
    if request.private_data is not None:
        demo.private_data = request.private_data

    # Persist changes to config file
    config = get_config()
    module_key = demo.module.strip().lower()
    for i, d in enumerate(config.demos):
        if d.id == demo_id:
            config.demos[i] = demo
            break
        if d.module.strip().lower() == module_key:
            config.demos[i] = demo
            break
    else:
        config.demos.append(demo)
    save_config(config)

    registry.register(demo, "configured")

    # Invalidate loader cache for this demo
    loader = get_demo_loader()
    loader.unload(demo_id)

    return DemoDetailResponse(
        demo=build_demo_summary(demo, "configured"),
        variants=demo.variants,
    )


@router.patch("/{demo_id}/agents/{agent_name}", response_model=AgentInfo)
async def update_agent(
    demo_id: str,
    agent_name: str,
    request: UpdateAgentRequest,
) -> AgentInfo:
    """Update an agent's runtime configuration.

    Modifies the live Agent instance in memory. Changes persist
    for the lifetime of the studio process.

    Args:
        demo_id: The demo ID.
        agent_name: The agent name.
        request: Fields to update.

    Returns:
        Updated agent info.

    Raises:
        HTTPException: If demo or agent not found.
    """
    registry = get_registry()
    demo = registry.get(demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {demo_id}")

    loader = get_demo_loader()
    loaded = loader.load(demo)
    agent = loaded.get_agent(agent_name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {agent_name} in demo {demo_id}",
        )

    # Apply updates to the live agent instance
    if request.description is not None:
        agent.description = request.description
    if request.system_prompt is not None:
        from langchain_core.messages import SystemMessage

        agent.system_prompt = request.system_prompt if request.system_prompt else None
        # Reset the internal system message so it gets recomputed
        if hasattr(agent, "_system_message"):
            agent._system_message = (
                SystemMessage(content=request.system_prompt) if request.system_prompt else None
            )
    if request.tags is not None:
        agent.tags = request.tags
    if request.memory_config is not None:
        agent.memory_config = request.memory_config
    if request.system_tools_config is not None:
        agent.system_tools_config = request.system_tools_config
    if request.orchestration_config is not None:
        agent.orchestration_config = request.orchestration_config
    if request.timeout is not None:
        agent.timeout = request.timeout
    if request.max_results is not None:
        agent.max_results = request.max_results
    if request.included_nested_synthesis is not None:
        agent.included_nested_synthesis = request.included_nested_synthesis
    if request.allow_private_in_system_tools is not None:
        agent.allow_private_in_system_tools = request.allow_private_in_system_tools
    if request.private_data is not None:
        agent.private_data = dict(request.private_data)

    # Build swarm membership info
    swarm_agents: dict[str, str] = {}
    for swarm in loaded.swarms:
        if hasattr(swarm, "agents"):
            for sa in swarm.agents:
                swarm_agents[getattr(sa, "name", str(sa))] = getattr(swarm, "name", str(swarm))

    return build_agent_info(agent, agent_name, swarm_agents)


@router.patch("/{demo_id}/swarms/{swarm_name}", response_model=SwarmInfo)
async def update_swarm(
    demo_id: str,
    swarm_name: str,
    request: UpdateSwarmRequest,
) -> SwarmInfo:
    """Update a swarm's runtime configuration.

    Args:
        demo_id: The demo ID.
        swarm_name: The swarm name.
        request: Fields to update.

    Returns:
        Updated swarm info.

    Raises:
        HTTPException: If demo or swarm not found.
    """
    registry = get_registry()
    demo = registry.get(demo_id)

    if demo is None:
        raise HTTPException(status_code=404, detail=f"Demo not found: {demo_id}")

    loader = get_demo_loader()
    loaded = loader.load(demo)
    swarm = loaded.get_swarm(swarm_name)

    if swarm is None:
        raise HTTPException(
            status_code=404,
            detail=f"Swarm not found: {swarm_name} in demo {demo_id}",
        )

    if request.description is not None:
        swarm.description = request.description
    if request.system_prompt is not None:
        from langchain_core.messages import SystemMessage

        swarm.system_prompt = request.system_prompt if request.system_prompt else None
        if hasattr(swarm, "_system_message"):
            swarm._system_message = (
                SystemMessage(content=request.system_prompt) if request.system_prompt else None
            )
    if request.tags is not None:
        swarm.tags = request.tags
    if request.memory_config is not None:
        swarm.memory_config = request.memory_config
    if request.system_tools_config is not None:
        swarm.system_tools_config = request.system_tools_config
    if request.orchestration_config is not None:
        swarm.orchestration_config = request.orchestration_config
    if request.allow_private_in_system_tools is not None:
        swarm.allow_private_in_system_tools = request.allow_private_in_system_tools
    if request.private_data is not None:
        swarm.private_data = dict(request.private_data)

    return build_swarm_info(swarm)
