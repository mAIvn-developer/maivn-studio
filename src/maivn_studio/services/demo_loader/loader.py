"""DemoLoader service for dynamically loading and caching demo modules."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from langchain_core.messages import HumanMessage
from maivn import Agent, Swarm

from maivn_studio.config.models import DemoConfig

from .models import DemoPrompt, LoadedDemo

logger = logging.getLogger(__name__)


# MARK: Demo Loader


class DemoLoader:
    """Service for dynamically loading and caching demo modules."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the demo loader.

        Args:
            base_path: Base path to add to sys.path for imports.
        """
        self._base_path = base_path or Path.cwd()
        self._cache: dict[str, LoadedDemo] = {}
        self._path_added = False

    def _ensure_path(self) -> None:
        """Ensure base path is in sys.path for imports."""
        if not self._path_added:
            path_str = str(self._base_path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
                logger.debug(f"Added {path_str} to sys.path")
            self._path_added = True

    def load(
        self,
        config: DemoConfig,
        force_reload: bool = False,
        variant: str | None = None,
    ) -> LoadedDemo:
        """Load a demo module.

        Args:
            config: Demo configuration with module path.
            force_reload: Force reload even if cached.
            variant: Optional variant ID to configure on the module (if supported).

        Returns:
            LoadedDemo with introspected agents/swarms/prompts.

        Raises:
            ImportError: If module cannot be imported.
        """
        cache_key = config.id if variant is None else f"{config.id}:{variant}"
        if not force_reload and cache_key in self._cache:
            loaded = self._cache[cache_key]
            # Reconfigure variant on cached modules if supported.
            self._apply_variant(loaded.module, variant)
            loaded.prompts = self._find_prompts(loaded.module, config)
            loaded.default_invocation = self._find_invocation_config(loaded.module)
            loaded.explicit_executor_name = self._find_executor_name(loaded.module)
            return loaded

        self._ensure_path()

        logger.info(f"Loading demo module: {config.module}")

        # Import the module
        try:
            module = importlib.import_module(config.module)
            if force_reload:
                module = importlib.reload(module)
        except ImportError as e:
            logger.error(f"Failed to import {config.module}: {e}")
            raise

        # Allow modules to configure themselves for a variant (optional hook).
        self._apply_variant(module, variant)

        # Find agents and swarms at module level
        agents = self._find_agents(module)
        swarms = self._find_swarms(module)

        # Find pre-defined prompts
        prompts = self._find_prompts(module, config)

        logger.debug(
            f"Loaded {config.id}: {len(agents)} agents, {len(swarms)} swarms, "
            f"{len(prompts)} prompts"
        )

        # Find default invocation config
        default_invocation = self._find_invocation_config(module)
        explicit_executor_name = self._find_executor_name(module)

        loaded = LoadedDemo(
            config=config,
            module=module,
            agents=agents,
            swarms=swarms,
            prompts=prompts,
            default_invocation=default_invocation,
            explicit_executor_name=explicit_executor_name,
        )

        self._cache[cache_key] = loaded
        return loaded

    def _find_agents(self, module: ModuleType) -> list[Agent]:
        """Find all Agent instances in a module."""
        agents: list[Agent] = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            if isinstance(obj, Agent):
                agents.append(obj)
        return agents

    def _find_swarms(self, module: ModuleType) -> list[Swarm]:
        """Find all Swarm instances in a module."""
        swarms: list[Swarm] = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = getattr(module, name)
            if isinstance(obj, Swarm):
                swarms.append(obj)
        return swarms

    def _find_invocation_config(self, module: ModuleType) -> dict[str, Any] | None:
        """Find DEMO_INVOCATION dict in a module.

        Looks for a module-level ``DEMO_INVOCATION`` dict whose keys match
        InvocationConfig fields (force_final_tool, model, reasoning,
        targeted_tools, metadata, allow_private_in_system_tools).
        """
        raw = getattr(module, "DEMO_INVOCATION", None)
        if not isinstance(raw, dict):
            return None

        allowed_keys = {
            "force_final_tool",
            "model",
            "reasoning",
            "targeted_tools",
            "metadata",
            "memory_config",
            "allow_private_in_system_tools",
        }
        return {k: v for k, v in raw.items() if k in allowed_keys}

    def _find_executor_name(self, module: ModuleType) -> str | None:
        raw = getattr(module, "DEMO_EXECUTOR", None)
        if raw is None:
            return None
        if not isinstance(raw, str):
            logger.warning(
                "Ignoring DEMO_EXECUTOR for %s because it is not a string",
                module.__name__,
            )
            return None
        name = raw.strip()
        return name or None

    def _find_prompts(self, module: ModuleType, config: DemoConfig) -> list[DemoPrompt]:
        """Find pre-defined prompts in a module.

        Looks for:
        - DEMO_PROMPTS: list of dicts with 'name', 'content', 'description'
        - DEFAULT_PROMPT: str - a default prompt string
        - messages: list[BaseMessage] - pre-defined message list
        - HumanMessage instances in module source (fallback)
        """
        prompts: list[DemoPrompt] = []
        prompt_id = 0

        # Look for DEMO_PROMPTS list
        if hasattr(module, "DEMO_PROMPTS"):
            demo_prompts = module.DEMO_PROMPTS
            if isinstance(demo_prompts, list):
                for i, p in enumerate(demo_prompts):
                    if isinstance(p, dict) and "content" in p:
                        prompts.append(
                            DemoPrompt(
                                id=f"{config.id}-prompt-{prompt_id}",
                                name=p.get("name", f"Prompt {i + 1}"),
                                content=p["content"],
                                description=p.get("description", ""),
                                is_default=p.get("is_default", i == 0),
                                source="module",
                                structured_output=p.get("structured_output"),
                                message_type=p.get("message_type"),
                                variant=p.get("variant"),
                            )
                        )
                        prompt_id += 1

        # Look for DEFAULT_PROMPT string
        if hasattr(module, "DEFAULT_PROMPT"):
            default_prompt = module.DEFAULT_PROMPT
            if isinstance(default_prompt, str):
                prompts.append(
                    DemoPrompt(
                        id=f"{config.id}-default",
                        name="Default Prompt",
                        content=default_prompt,
                        description="Default prompt from module",
                        is_default=True,
                        source="module",
                    )
                )

        # Look for messages list at module level (common pattern in demos)
        if hasattr(module, "messages"):
            messages = module.messages
            if isinstance(messages, list) and messages:
                # Extract content from HumanMessage
                for msg in messages:
                    if isinstance(msg, HumanMessage):
                        content = msg.content if isinstance(msg.content, str) else str(msg.content)
                        prompts.append(
                            DemoPrompt(
                                id=f"{config.id}-messages-{prompt_id}",
                                name="Pre-defined Message",
                                content=content,
                                description="Pre-defined message from module",
                                is_default=len(prompts) == 0,
                                source="module",
                            )
                        )
                        prompt_id += 1

        # If no prompts found, try extracting from source code
        if not prompts:
            prompts = self._extract_prompts_from_source(module, config, prompt_id)

        return prompts

    def _extract_prompts_from_source(
        self, module: ModuleType, config: DemoConfig, start_id: int
    ) -> list[DemoPrompt]:
        """Extract HumanMessage content from module source code.

        This is a fallback when prompts aren't available at module level.
        Parses source to find HumanMessage content strings.

        Args:
            module: The loaded module.
            config: Demo configuration.
            start_id: Starting ID for prompts.

        Returns:
            List of extracted prompts.
        """
        import ast
        import inspect

        prompts: list[DemoPrompt] = []
        prompt_id = start_id

        try:
            source = inspect.getsource(module)
        except (OSError, TypeError):
            return prompts

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return prompts

        class HumanMessageExtractor(ast.NodeVisitor):
            """AST visitor to extract HumanMessage content."""

            def __init__(self) -> None:
                self.contents: list[str] = []

            def visit_Call(self, node: ast.Call) -> Any:  # noqa: N802
                # Look for HumanMessage(content=...) calls
                if isinstance(node.func, ast.Name) and node.func.id == "HumanMessage":
                    for keyword in node.keywords:
                        if keyword.arg == "content":
                            content = self._extract_string(keyword.value)
                            if content:
                                self.contents.append(content)
                    # Also check positional argument
                    if node.args:
                        content = self._extract_string(node.args[0])
                        if content:
                            self.contents.append(content)
                self.generic_visit(node)

            def _extract_string(self, node: ast.expr) -> str | None:
                """Extract string value from AST node."""
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    return node.value
                if isinstance(node, ast.JoinedStr):
                    # f-string - skip for now as it may contain variables
                    return None
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
                    # String concatenation
                    left = self._extract_string(node.left)
                    right = self._extract_string(node.right)
                    if left and right:
                        return left + right
                return None

        extractor = HumanMessageExtractor()
        extractor.visit(tree)

        for i, content in enumerate(extractor.contents):
            # Clean up the content (normalize whitespace)
            content = " ".join(content.split())
            if content:
                prompts.append(
                    DemoPrompt(
                        id=f"{config.id}-extracted-{prompt_id}",
                        name=f"Prompt {i + 1}" if len(extractor.contents) > 1 else "Demo Prompt",
                        content=content,
                        description="Extracted from demo source",
                        is_default=i == 0,
                        source="source",
                    )
                )
                prompt_id += 1

        return prompts

    def get(self, demo_id: str) -> LoadedDemo | None:
        """Get a cached loaded demo."""
        return self._cache.get(demo_id)

    def unload(self, demo_id: str) -> None:
        """Remove a demo from cache."""
        keys = [key for key in self._cache if key == demo_id or key.startswith(f"{demo_id}:")]
        for key in keys:
            del self._cache[key]

    def clear_cache(self) -> None:
        """Clear all cached demos."""
        self._cache.clear()

    def _apply_variant(self, module: ModuleType, variant: str | None) -> None:
        """Apply an optional variant configuration to a module if it supports it."""
        if not hasattr(module, "configure_variant"):
            return
        configure_variant = module.configure_variant
        if not callable(configure_variant):
            return
        try:
            configure_variant(variant)
        except Exception as exc:
            logger.warning(f"Failed to apply variant {variant} for {module.__name__}: {exc}")


# MARK: Global Loader

_loader: DemoLoader | None = None


def get_demo_loader() -> DemoLoader:
    """Get the global demo loader instance."""
    global _loader
    if _loader is None:
        _loader = DemoLoader()
    return _loader


def init_demo_loader(base_path: Path) -> DemoLoader:
    """Initialize the global demo loader.

    Args:
        base_path: Base path for module imports.

    Returns:
        The initialized loader.
    """
    global _loader
    _loader = DemoLoader(base_path)
    return _loader
