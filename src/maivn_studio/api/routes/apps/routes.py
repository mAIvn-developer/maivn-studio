"""API route handlers for app management."""

# pyright: strict

from __future__ import annotations

import logging
from typing import Literal, cast

from fastapi import APIRouter, HTTPException

from maivn_studio.config.models import AppConfig, PrivateDataField
from maivn_studio.discovery.registry import get_registry
from maivn_studio.services.app_loader.errors import AppLoadError
from maivn_studio.services.app_loader.loader import get_app_loader

from .introspection import build_agent_info, build_app_summary, build_swarm_info, build_tool_info
from .models import (
    AgentInfo,
    AppDetailResponse,
    AppFullDetailsResponse,
    AppListResponse,
    PromptInfo,
    SwarmInfo,
    ToolInfo,
    UpdateAgentRequest,
    UpdateAppRequest,
    UpdateSwarmRequest,
)

router = APIRouter(prefix="/api/apps", tags=["apps"])
logger = logging.getLogger(__name__)


# MARK: Helpers


def calculate_app_runtime_tool_count(agents: list[AgentInfo], swarms: list[SwarmInfo]) -> int:
    """Count app runtime tools without double-counting swarm member agents."""
    standalone_agent_tools = sum(
        agent.runtime_tool_count for agent in agents if not agent.is_swarm_member
    )
    swarm_tools = sum(swarm.runtime_tool_count for swarm in swarms)
    return standalone_agent_tools + swarm_tools


def _resolve_app_variant(app: AppConfig, requested_variant: str | None = None) -> str | None:
    """Resolve the effective variant for an app, honoring configured defaults."""
    variant = requested_variant or app.default_variant
    if not variant:
        return None
    if variant in app.variants:
        return variant

    logger.warning(
        "Ignoring invalid default variant %r for app %s; available variants: %s",
        variant,
        app.id,
        sorted(app.variants.keys()),
    )
    return None


def _build_private_data_defaults(
    app: AppConfig, resolved_variant: str | None
) -> dict[str, str | int | bool]:
    """Build the effective private data defaults for an app details view."""
    defaults = dict(app.private_data)
    if resolved_variant:
        defaults.update(app.variants[resolved_variant].private_data)
    return defaults


def _infer_private_data_type(value: str | int | bool) -> str:
    """Infer the Studio field type for a configured private data value."""
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "number"
    return "string"


def merge_private_data_schema(
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


def _build_unloadable_app_details(
    app: AppConfig,
    *,
    source: Literal["configured", "discovered"],
    resolved_variant: str | None,
    load_error: AppLoadError,
) -> AppFullDetailsResponse:
    """Return registry metadata when the app module cannot be imported."""
    private_data_defaults = _build_private_data_defaults(app, resolved_variant)
    missing_modules = [load_error.missing_module] if load_error.missing_module else []
    return AppFullDetailsResponse(
        id=app.id,
        name=app.name,
        description=app.description,
        module=app.module,
        category=app.category,
        tags=app.tags,
        variants=app.variants,
        source=source,
        privateDataSchema=merge_private_data_schema([], private_data_defaults),
        privateDataDefaults=private_data_defaults,
        loadable=False,
        load_error=str(load_error),
        missing_modules=missing_modules,
    )


# MARK: Read Routes


@router.get("", response_model=AppListResponse)
async def list_apps(category: str | None = None) -> AppListResponse:
    """List all available apps.

    Args:
        category: Optional category filter.

    Returns:
        List of apps with metadata.
    """
    registry = get_registry()

    if category:
        apps = registry.get_by_category(category)
    else:
        apps = registry.apps

    app_summaries = [build_app_summary(app, registry.get_source(app.id)) for app in apps]

    return AppListResponse(
        apps=app_summaries,
        total=len(apps),
        categories=registry.categories,
    )


@router.get("/categories", response_model=list[str])
async def list_categories() -> list[str]:
    """List all app categories.

    Returns:
        List of category names.
    """
    registry = get_registry()
    return registry.categories


@router.get("/{app_id}", response_model=AppDetailResponse)
async def get_app(app_id: str) -> AppDetailResponse:
    """Get details for a specific app.

    Args:
        app_id: The app ID.

    Returns:
        App details including variants.

    Raises:
        HTTPException: If app not found.
    """
    registry = get_registry()
    app = registry.get(app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {app_id}")

    return AppDetailResponse(
        app=build_app_summary(app, registry.get_source(app_id)),
        variants=app.variants,
    )


@router.get("/{app_id}/details", response_model=AppFullDetailsResponse)
async def get_app_full_details(app_id: str, variant: str | None = None) -> AppFullDetailsResponse:
    """Get full details for an app including private data schema.

    Args:
        app_id: The app ID.
        variant: Optional app variant to load.

    Returns:
        Full app details.

    Raises:
        HTTPException: If app not found.
    """
    registry = get_registry()
    app = registry.get(app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {app_id}")

    # Load the app to get full details
    loader = get_app_loader()
    resolved_variant = _resolve_app_variant(app, variant)
    try:
        loaded = loader.load(app, variant=resolved_variant)
    except AppLoadError as exc:
        return _build_unloadable_app_details(
            app,
            source=registry.get_source(app_id),
            resolved_variant=resolved_variant,
            load_error=exc,
        )

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
        except Exception:  # noqa: BLE001 - one bad agent shouldn't fail the whole tools listing
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
        if prompt_variant and prompt_variant not in app.variants:
            logger.warning(
                "Ignoring invalid prompt variant %r for app %s prompt %r; available variants: %s",
                prompt_variant,
                app_id,
                prompt_name or f"Prompt {i + 1}",
                sorted(app.variants.keys()),
            )
            prompt_variant = None
        prompts.append(
            PromptInfo(
                id=f"{app_id}-prompt-{i}",
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

    private_data_defaults = _build_private_data_defaults(app, resolved_variant)
    private_data_schema = merge_private_data_schema(
        extract_private_data_schema(loaded),
        private_data_defaults,
    )

    return AppFullDetailsResponse(
        id=app.id,
        name=app.name,
        description=app.description,
        module=app.module,
        category=app.category,
        tags=app.tags,
        variants=app.variants,
        source=registry.get_source(app_id),
        agents=agents,
        swarms=swarms,
        tools=tools,
        prompts=prompts,
        privateDataSchema=private_data_schema,
        privateDataDefaults=private_data_defaults,
        defaultInvocation=loaded.default_invocation,
        runtime_tool_count=calculate_app_runtime_tool_count(agents, swarms),
    )


# MARK: Update Routes


@router.patch("/{app_id}", response_model=AppDetailResponse)
async def update_app(app_id: str, request: UpdateAppRequest) -> AppDetailResponse:
    """Update an app's configuration.

    Args:
        app_id: The app ID.
        request: Fields to update.

    Returns:
        Updated app details.

    Raises:
        HTTPException: If app not found.
    """
    from maivn_studio.config.loader import get_config, save_config

    registry = get_registry()
    app = registry.get(app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {app_id}")

    # Apply updates to in-memory config
    if request.name is not None:
        app.name = request.name
    if request.description is not None:
        app.description = request.description
    if request.category is not None:
        app.category = request.category
    if request.tags is not None:
        app.tags = request.tags
    if request.variants is not None:
        app.variants = request.variants
    if request.private_data is not None:
        app.private_data = request.private_data

    # Persist changes to config file
    config = get_config()
    module_key = app.module.strip().lower()
    for i, a in enumerate(config.apps):
        if a.id == app_id:
            config.apps[i] = app
            break
        if a.module.strip().lower() == module_key:
            config.apps[i] = app
            break
    else:
        config.apps.append(app)
    save_config(config)

    registry.register(app, "configured")

    # Invalidate loader cache for this app
    loader = get_app_loader()
    loader.unload(app_id)

    return AppDetailResponse(
        app=build_app_summary(app, "configured"),
        variants=app.variants,
    )


@router.patch("/{app_id}/agents/{agent_name}", response_model=AgentInfo)
async def update_agent(
    app_id: str,
    agent_name: str,
    request: UpdateAgentRequest,
) -> AgentInfo:
    """Update an agent's runtime configuration.

    Modifies the live Agent instance in memory. Changes persist
    for the lifetime of the studio process.

    Args:
        app_id: The app ID.
        agent_name: The agent name.
        request: Fields to update.

    Returns:
        Updated agent info.

    Raises:
        HTTPException: If app or agent not found.
    """
    registry = get_registry()
    app = registry.get(app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {app_id}")

    loader = get_app_loader()
    try:
        loaded = loader.load(app)
    except AppLoadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    agent = loaded.get_agent(agent_name)

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent not found: {agent_name} in app {app_id}",
        )

    # Apply updates to the live agent instance
    if request.description is not None:
        agent.description = request.description
    if request.system_prompt is not None:
        new_system_prompt = request.system_prompt if request.system_prompt else None
        agent.system_prompt = new_system_prompt
        # Re-point the resolved system message via the SDK's public setter, which
        # applies the same normalization used at construction time.
        agent.set_system_message(new_system_prompt)
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
        # SDK ``private_data`` is typed ``dict[object, object]``; widen the
        # request's ``dict[str, Any]`` to match the invariant field type.
        agent.private_data = cast("dict[object, object]", dict(request.private_data))

    # Build swarm membership info
    swarm_agents: dict[str, str] = {}
    for swarm in loaded.swarms:
        if hasattr(swarm, "agents"):
            for sa in swarm.agents:
                swarm_agents[getattr(sa, "name", str(sa))] = getattr(swarm, "name", str(swarm))

    return build_agent_info(agent, agent_name, swarm_agents)


@router.patch("/{app_id}/swarms/{swarm_name}", response_model=SwarmInfo)
async def update_swarm(
    app_id: str,
    swarm_name: str,
    request: UpdateSwarmRequest,
) -> SwarmInfo:
    """Update a swarm's runtime configuration.

    Args:
        app_id: The app ID.
        swarm_name: The swarm name.
        request: Fields to update.

    Returns:
        Updated swarm info.

    Raises:
        HTTPException: If app or swarm not found.
    """
    registry = get_registry()
    app = registry.get(app_id)

    if app is None:
        raise HTTPException(status_code=404, detail=f"App not found: {app_id}")

    loader = get_app_loader()
    try:
        loaded = loader.load(app)
    except AppLoadError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    swarm = loaded.get_swarm(swarm_name)

    if swarm is None:
        raise HTTPException(
            status_code=404,
            detail=f"Swarm not found: {swarm_name} in app {app_id}",
        )

    if request.description is not None:
        swarm.description = request.description
    if request.system_prompt is not None:
        new_system_prompt = request.system_prompt if request.system_prompt else None
        swarm.system_prompt = new_system_prompt
        # See update_agent: re-point the resolved system message via the SDK's
        # public setter, which applies the construction-time normalization.
        swarm.set_system_message(new_system_prompt)
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
        swarm.private_data = cast("dict[object, object]", dict(request.private_data))

    return build_swarm_info(swarm)
