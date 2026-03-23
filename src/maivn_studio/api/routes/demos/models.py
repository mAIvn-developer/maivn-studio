"""Pydantic models for demo API requests and responses."""

from __future__ import annotations

from typing import Any, Literal

from maivn_shared import MemoryConfig
from pydantic import BaseModel, Field

from maivn_studio.config.models import DemoVariant, PrivateDataField

# MARK: Response Models


class DemoSummary(BaseModel):
    """Shared demo summary returned by demo APIs."""

    id: str
    name: str
    description: str = ""
    module: str
    category: str = "uncategorized"
    tags: list[str] = Field(default_factory=list)
    variants: dict[str, DemoVariant] = Field(default_factory=dict)
    private_data: dict[str, str | int | bool] = Field(default_factory=dict)
    source: Literal["configured", "discovered"] = "configured"


class DemoListResponse(BaseModel):
    """Response for listing demos."""

    demos: list[DemoSummary]
    total: int
    categories: list[str]


class DemoDetailResponse(BaseModel):
    """Response for demo details."""

    demo: DemoSummary
    variants: dict[str, DemoVariant]


class DependencyInfo(BaseModel):
    """Dependency information for a tool."""

    name: str
    dependency_type: str  # agent, tool, data, user
    arg_name: str
    data_key: str | None = None
    tool_id: str | None = None
    agent_id: str | None = None
    prompt: str | None = None
    input_type: str | None = None


class AgentInfo(BaseModel):
    """Agent information with full SDK surface."""

    name: str
    description: str
    system_prompt: str | None = None
    tags: list[str] = Field(default_factory=list)
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)
    private_data: dict[str, Any] = Field(default_factory=dict)
    tool_count: int = 0
    runtime_tool_count: int = 0
    timeout: float | None = None
    max_results: int | None = None
    use_as_final_output: bool = False
    included_nested_synthesis: bool | Literal["auto"] = "auto"
    allow_private_in_system_tools: bool = False
    hook_execution_mode: str = "tool"
    has_before_hook: bool = False
    has_after_hook: bool = False
    mcp_server_names: list[str] = Field(default_factory=list)
    private_data_keys: list[str] = Field(default_factory=list)
    is_swarm_member: bool = False
    swarm: str | None = None


class SwarmInfo(BaseModel):
    """Swarm information with full SDK surface."""

    name: str
    description: str = ""
    system_prompt: str | None = None
    tags: list[str] = Field(default_factory=list)
    memory_config: MemoryConfig = Field(default_factory=MemoryConfig)
    allow_private_in_system_tools: bool = False
    private_data: dict[str, Any] = Field(default_factory=dict)
    agent_count: int = 0
    agent_names: list[str] = Field(default_factory=list)
    tool_count: int = 0
    runtime_tool_count: int = 0
    private_data_keys: list[str] = Field(default_factory=list)


class ToolInfo(BaseModel):
    """Tool information with full SDK surface."""

    name: str
    description: str
    agent: str
    tool_type: str = "func"
    final_tool: bool = False
    always_execute: bool = False
    tags: list[str] = Field(default_factory=list)
    dependencies: list[DependencyInfo] = Field(default_factory=list)
    args_schema: dict[str, Any] | None = None


class PromptInfo(BaseModel):
    """Prompt information."""

    id: str
    name: str
    content: str
    description: str = ""
    is_default: bool = False
    source: str = "discovered"
    structured_output: str | None = None  # Tool name for structured output
    message_type: str | None = None  # Auto-select message type (human, redacted)
    variant: str | None = None  # Auto-select variant when prompt is chosen


class DemoFullDetailsResponse(BaseModel):
    """Full demo details including agents, tools, and private data schema."""

    id: str
    name: str
    description: str
    module: str
    category: str
    tags: list[str] = Field(default_factory=list)
    variants: dict[str, DemoVariant] = Field(default_factory=dict)
    source: Literal["configured", "discovered"] = "configured"
    agents: list[AgentInfo] = Field(default_factory=list)
    swarms: list[SwarmInfo] = Field(default_factory=list)
    tools: list[ToolInfo] = Field(default_factory=list)
    prompts: list[PromptInfo] = Field(default_factory=list)
    privateDataSchema: list[PrivateDataField] = Field(default_factory=list)
    defaultInvocation: dict[str, Any] | None = None
    runtime_tool_count: int = 0


# MARK: Request Models


class UpdateDemoRequest(BaseModel):
    """Request to update a demo configuration."""

    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    variants: dict[str, DemoVariant] | None = None
    private_data: dict[str, str | int | bool] | None = None


class UpdateAgentRequest(BaseModel):
    """Request to update an agent's runtime configuration."""

    description: str | None = None
    system_prompt: str | None = None
    tags: list[str] | None = None
    memory_config: MemoryConfig | None = None
    timeout: float | None = Field(default=None, ge=0)
    max_results: int | None = Field(default=None, ge=1)
    included_nested_synthesis: bool | Literal["auto"] | None = None
    allow_private_in_system_tools: bool | None = None
    private_data: dict[str, Any] | None = None


class UpdateSwarmRequest(BaseModel):
    """Request to update a swarm's runtime configuration."""

    description: str | None = None
    system_prompt: str | None = None
    tags: list[str] | None = None
    memory_config: MemoryConfig | None = None
    allow_private_in_system_tools: bool | None = None
    private_data: dict[str, Any] | None = None
