"""Data models for loaded apps and prompts."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any

from maivn import Agent, Swarm

from maivn_studio.config.models import AppConfig

logger = logging.getLogger(__name__)


# MARK: Prompt


@dataclass
class AppPrompt:
    """A pre-defined or saved prompt for an app."""

    id: str
    name: str
    content: str
    description: str = ""
    is_default: bool = False
    source: str = "module"  # 'module', 'config', 'user'
    structured_output: str | None = None  # Tool name for structured output
    message_type: str | None = None  # Auto-select message type (human, redacted)
    variant: str | None = None  # Auto-select variant when prompt is chosen


# MARK: Loaded App


@dataclass
class LoadedApp:
    """A loaded and introspected app module."""

    config: AppConfig
    module: ModuleType
    agents: list[Agent] = field(default_factory=list)
    swarms: list[Swarm] = field(default_factory=list)
    prompts: list[AppPrompt] = field(default_factory=list)
    default_invocation: dict[str, Any] | None = None
    explicit_executor_name: str | None = None

    @property
    def executor(self) -> Agent | Swarm | None:
        """Get the primary executor (explicit override, else swarm, else agent)."""
        explicit_name = (
            self.explicit_executor_name.strip()
            if isinstance(self.explicit_executor_name, str)
            else ""
        )
        if explicit_name:
            resolved = self.get_agent(explicit_name) or self.get_swarm(explicit_name)
            if resolved is not None:
                return resolved
            logger.warning(
                "App %s requested APP_EXECUTOR=%r but no matching agent or swarm was found",
                self.config.id,
                explicit_name,
            )
        if self.swarms:
            return self.swarms[0]
        if self.agents:
            return self.agents[0]
        return None

    @property
    def executor_type(self) -> str:
        """Get the type of executor ('swarm', 'agent', or 'none')."""
        executor = self.executor
        if executor is None:
            return "none"
        if any(executor is swarm for swarm in self.swarms):
            return "swarm"
        if any(executor is agent for agent in self.agents):
            return "agent"
        return "agent"

    @property
    def executor_name(self) -> str:
        """Get the name of the primary executor."""
        executor = self.executor
        if executor and executor.name:
            return executor.name
        return ""

    @property
    def has_executor(self) -> bool:
        """Check if app has an executable agent or swarm."""
        return self.executor is not None

    def get_agent(self, name: str) -> Agent | None:
        """Get an agent by name."""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None

    def get_swarm(self, name: str) -> Swarm | None:
        """Get a swarm by name."""
        for swarm in self.swarms:
            if swarm.name == name:
                return swarm
        return None

    def get_default_prompt(self) -> AppPrompt | None:
        """Get the default prompt if one exists."""
        for prompt in self.prompts:
            if prompt.is_default:
                return prompt
        return self.prompts[0] if self.prompts else None

    def get_prompt(self, prompt_id: str) -> AppPrompt | None:
        """Get a prompt by ID."""
        for prompt in self.prompts:
            if prompt.id == prompt_id:
                return prompt
        return None

    def get_tools(self) -> list[dict[str, Any]]:
        """Get all tools registered across all agents."""
        tools: list[dict[str, Any]] = []
        seen_names: set[str] = set()

        for agent in self.agents:
            if hasattr(agent, "_tool_repo") and agent._tool_repo:
                for tool in agent._tool_repo.list_tools():
                    if tool.name not in seen_names:
                        tools.append(
                            {
                                "name": tool.name,
                                "description": tool.description or "",
                                "agent": agent.name,
                                "final_tool": getattr(tool, "final_tool", False),
                            }
                        )
                        seen_names.add(tool.name)

        return tools

    def get_all_agents(self) -> list[dict[str, Any]]:
        """Get metadata for all agents (including swarm members)."""
        result: list[dict[str, Any]] = []

        # Standalone agents
        for agent in self.agents:
            result.append(
                {
                    "name": agent.name,
                    "description": agent.description or "",
                    "is_swarm_member": False,
                }
            )

        # Swarm member agents
        for swarm in self.swarms:
            if hasattr(swarm, "agents"):
                for agent in swarm.agents:
                    result.append(
                        {
                            "name": agent.name,
                            "description": agent.description or "",
                            "is_swarm_member": True,
                            "swarm": swarm.name,
                        }
                    )

        return result
