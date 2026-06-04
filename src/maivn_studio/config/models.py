"""Pydantic configuration models for maivn-studio."""

# pyright: strict

from __future__ import annotations

from pydantic import BaseModel, Field

# MARK: App Configuration


class AppVariant(BaseModel):
    """A variant configuration for an app."""

    args: list[str] = Field(default_factory=list)
    description: str = ""
    private_data: dict[str, str | int | bool] = Field(default_factory=dict)


class AppConfig(BaseModel):
    """Configuration for a single app."""

    id: str
    name: str
    description: str = ""
    module: str
    category: str = "uncategorized"
    tags: list[str] = Field(default_factory=list)
    variants: dict[str, AppVariant] = Field(default_factory=dict)
    default_variant: str | None = None
    private_data: dict[str, str | int | bool] = Field(default_factory=dict)


# MARK: Agent/Swarm Configuration


class AgentConfig(BaseModel):
    """Configuration for an agent reference."""

    id: str
    name: str
    app: str
    description: str = ""


class SwarmConfig(BaseModel):
    """Configuration for a swarm reference."""

    id: str
    name: str
    app: str
    agents: list[str] = Field(default_factory=list)
    final_agent: str | None = None


# MARK: Private Data Schema


class PrivateDataField(BaseModel):
    """Schema definition for a private_data field."""

    key: str
    label: str = ""
    type: str = "string"  # string, number, boolean
    required: bool = False
    default_value: str | int | bool | None = None
    description: str = ""


# MARK: Saved Prompts


class SavedPrompt(BaseModel):
    """A user-saved prompt for an app."""

    id: str
    name: str
    content: str
    description: str = ""
    app_id: str  # The app this prompt is for
    message_type: str = "human"  # human, redacted, system
    created_at: str | None = None


# MARK: Discovery Configuration


class DiscoveryConfig(BaseModel):
    """Configuration for app auto-discovery."""

    paths: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=lambda: ["__pycache__", ".pytest_cache"])


# MARK: Environment Configuration


class EnvConfig(BaseModel):
    """Environment configuration."""

    file: str = ".env"
    required: list[str] = Field(default_factory=list)


# MARK: Studio Settings


class StudioSettings(BaseModel):
    """Core studio server settings."""

    name: str = "MAIVN Studio"
    version: str = "0.1.0"
    host: str = "127.0.0.1"
    port: int = 8080
    debug: bool = False


# MARK: Root Configuration


class StudioConfig(BaseModel):
    """Root configuration for maivn-studio."""

    studio: StudioSettings = Field(default_factory=StudioSettings)
    env: EnvConfig = Field(default_factory=EnvConfig)
    discovery: DiscoveryConfig = Field(default_factory=DiscoveryConfig)
    apps: list[AppConfig] = Field(default_factory=list)
    agents: list[AgentConfig] = Field(default_factory=list)
    swarms: list[SwarmConfig] = Field(default_factory=list)
    saved_prompts: list[SavedPrompt] = Field(default_factory=list)
