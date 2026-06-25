"""AppLoader service for dynamically loading and caching app modules."""

# pyright: strict
from __future__ import annotations

import ast
import importlib
import inspect
import logging
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

from langchain_core.messages import HumanMessage
from maivn import Agent, Swarm
from typing_extensions import override

from maivn_studio.config.models import AppConfig

from .errors import AppLoadError
from .models import AppPrompt, LoadedApp

logger = logging.getLogger(__name__)


# MARK: Configuration

# Keys recognised in a module-level ``APP_INVOCATION`` dict. They mirror the
# fields of the SDK InvocationConfig.
INVOCATION_KEYS: frozenset[str] = frozenset(
    {
        "force_final_tool",
        "model",
        "reasoning",
        "targeted_tools",
        "metadata",
        "memory_config",
        "system_tools_config",
        "orchestration_config",
        "allow_private_in_system_tools",
    }
)


# MARK: Helpers


def _module_attr(module: ModuleType, name: str, default: object = None) -> object:
    """Read a module attribute as a plain ``object``.

    ``getattr`` on a dynamic name returns ``Any``; this isolates that untyped
    boundary in one place so callers narrow with ``isinstance`` from ``object``.
    """
    return cast(object, getattr(module, name, default))


def _as_str(value: object) -> str | None:
    """Return ``value`` as a string when it already is one, else ``None``."""
    return value if isinstance(value, str) else None


# MARK: App Loader


class AppLoader:
    """Service for dynamically loading and caching app modules."""

    def __init__(self, base_path: Path | None = None) -> None:
        """Initialize the app loader.

        Args:
            base_path: Base path to add to sys.path for imports.
        """
        self._base_path: Path = base_path or Path.cwd()
        self.cache: dict[str, LoadedApp] = {}
        self._path_added: bool = False

    def _ensure_path(self) -> None:
        """Ensure base path is in sys.path for imports."""
        if not self._path_added:
            path_str = str(self._base_path)
            if path_str not in sys.path:
                sys.path.insert(0, path_str)
                logger.debug("Added %s to sys.path", path_str)
            self._path_added = True

    def load(
        self,
        config: AppConfig,
        force_reload: bool = False,
        variant: str | None = None,
    ) -> LoadedApp:
        """Load an app module.

        Args:
            config: App configuration with module path.
            force_reload: Force reload even if cached.
            variant: Optional variant ID to configure on the module (if supported).

        Returns:
            LoadedApp with introspected agents/swarms/prompts.

        Raises:
            ImportError: If module cannot be imported.
        """
        cache_key = config.id if variant is None else f"{config.id}:{variant}"
        if not force_reload and cache_key in self.cache:
            loaded = self.cache[cache_key]
            # Reconfigure variant on cached modules if supported.
            self.apply_variant(loaded.module, variant)
            loaded.prompts = self.find_prompts(loaded.module, config)
            loaded.default_invocation = self.find_invocation_config(loaded.module)
            loaded.explicit_executor_name = self.find_executor_name(loaded.module)
            return loaded

        self._ensure_path()

        logger.info("Loading app module: %s", config.module)

        # Import the module
        try:
            module = importlib.import_module(config.module)
            if force_reload:
                module = importlib.reload(module)
        except ImportError as e:
            logger.error("Failed to import %s: %s", config.module, e)
            raise AppLoadError(config.module, e) from e

        # Allow modules to configure themselves for a variant (optional hook).
        self.apply_variant(module, variant)

        # Find agents and swarms at module level
        agents = self.find_agents(module)
        swarms = self.find_swarms(module)

        # Find pre-defined prompts
        prompts = self.find_prompts(module, config)

        logger.debug(
            "Loaded %s: %d agents, %d swarms, %d prompts",
            config.id,
            len(agents),
            len(swarms),
            len(prompts),
        )

        # Find default invocation config
        default_invocation = self.find_invocation_config(module)
        explicit_executor_name = self.find_executor_name(module)

        loaded = LoadedApp(
            config=config,
            module=module,
            agents=agents,
            swarms=swarms,
            prompts=prompts,
            default_invocation=default_invocation,
            explicit_executor_name=explicit_executor_name,
        )

        self.cache[cache_key] = loaded
        return loaded

    # MARK: - Introspection

    def find_agents(self, module: ModuleType) -> list[Agent]:
        """Find all Agent instances in a module."""
        agents: list[Agent] = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = _module_attr(module, name)
            if isinstance(obj, Agent):
                agents.append(obj)
        return agents

    def find_swarms(self, module: ModuleType) -> list[Swarm]:
        """Find all Swarm instances in a module."""
        swarms: list[Swarm] = []
        for name in dir(module):
            if name.startswith("_"):
                continue
            obj = _module_attr(module, name)
            if isinstance(obj, Swarm):
                swarms.append(obj)
        return swarms

    def find_invocation_config(self, module: ModuleType) -> dict[str, object] | None:
        """Find an invocation-defaults dict in a module.

        Looks for a module-level ``APP_INVOCATION`` dict whose keys match
        InvocationConfig fields (force_final_tool, model, reasoning,
        targeted_tools, metadata, memory_config, system_tools_config,
        orchestration_config, allow_private_in_system_tools).
        """
        raw = _module_attr(module, "APP_INVOCATION")
        if not isinstance(raw, dict):
            return None

        items = cast("dict[object, object]", raw)
        return {str(key): value for key, value in items.items() if key in INVOCATION_KEYS}

    def find_executor_name(self, module: ModuleType) -> str | None:
        """Find the optional module-level ``APP_EXECUTOR`` agent/swarm name."""
        raw = _module_attr(module, "APP_EXECUTOR")
        if raw is None:
            return None
        if not isinstance(raw, str):
            logger.warning(
                "Ignoring APP_EXECUTOR for %s because it is not a string",
                module.__name__,
            )
            return None
        name = raw.strip()
        return name or None

    def find_prompts(self, module: ModuleType, config: AppConfig) -> list[AppPrompt]:
        """Find pre-defined prompts in a module.

        Looks for:
        - APP_PROMPTS: list of dicts with 'name', 'content', 'description'
        - DEFAULT_PROMPT: str - a default prompt string
        - messages: list[BaseMessage] - pre-defined message list
        - HumanMessage instances in module source (fallback)
        """
        prompts: list[AppPrompt] = []
        prompt_id = 0

        # Look for APP_PROMPTS list
        app_prompts = _module_attr(module, "APP_PROMPTS")
        if isinstance(app_prompts, list):
            entries = cast("list[object]", app_prompts)
            for i, entry in enumerate(entries):
                if not isinstance(entry, dict):
                    continue
                spec = cast("dict[object, object]", entry)
                content = _as_str(spec.get("content"))
                if content is None:
                    continue
                prompts.append(
                    AppPrompt(
                        id=f"{config.id}-prompt-{prompt_id}",
                        name=_as_str(spec.get("name")) or f"Prompt {i + 1}",
                        content=content,
                        description=_as_str(spec.get("description")) or "",
                        is_default=bool(spec.get("is_default", i == 0)),
                        source="module",
                        structured_output=_as_str(spec.get("structured_output")),
                        message_type=_as_str(spec.get("message_type")),
                        variant=_as_str(spec.get("variant")),
                    )
                )
                prompt_id += 1

        # Look for DEFAULT_PROMPT string
        default_prompt = _as_str(_module_attr(module, "DEFAULT_PROMPT"))
        if default_prompt is not None:
            prompts.append(
                AppPrompt(
                    id=f"{config.id}-default",
                    name="Default Prompt",
                    content=default_prompt,
                    description="Default prompt from module",
                    is_default=True,
                    source="module",
                )
            )

        # Look for messages list at module level (common pattern in apps)
        messages = _module_attr(module, "messages")
        if isinstance(messages, list) and messages:
            message_entries = cast("list[object]", messages)
            for msg in message_entries:
                if not isinstance(msg, HumanMessage):
                    continue
                # langchain_core types message content as str | list[str | dict] with
                # untyped dict members; treat it as object and stringify non-str content.
                raw_content = cast(object, msg.content)
                content = raw_content if isinstance(raw_content, str) else str(raw_content)
                prompts.append(
                    AppPrompt(
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
        self, module: ModuleType, config: AppConfig, start_id: int
    ) -> list[AppPrompt]:
        """Extract HumanMessage content from module source code.

        This is a fallback when prompts aren't available at module level.
        Parses source to find HumanMessage content strings.

        Args:
            module: The loaded module.
            config: App configuration.
            start_id: Starting ID for prompts.

        Returns:
            List of extracted prompts.
        """
        prompts: list[AppPrompt] = []
        prompt_id = start_id

        try:
            source = inspect.getsource(module)
        except (OSError, TypeError):
            return prompts

        try:
            tree = ast.parse(source)
        except SyntaxError:
            return prompts

        extractor = _HumanMessageExtractor()
        extractor.visit(tree)

        contents = extractor.contents
        for i, content in enumerate(contents):
            # Clean up the content (normalize whitespace)
            content = " ".join(content.split())
            if content:
                prompts.append(
                    AppPrompt(
                        id=f"{config.id}-extracted-{prompt_id}",
                        name=f"Prompt {i + 1}" if len(contents) > 1 else "App Prompt",
                        content=content,
                        description="Extracted from app source",
                        is_default=i == 0,
                        source="source",
                    )
                )
                prompt_id += 1

        return prompts

    # MARK: - Cache Management

    def get(self, app_id: str) -> LoadedApp | None:
        """Get a cached loaded app."""
        return self.cache.get(app_id)

    def unload(self, app_id: str) -> None:
        """Remove an app from cache."""
        keys = [key for key in self.cache if key == app_id or key.startswith(f"{app_id}:")]
        for key in keys:
            del self.cache[key]

    def clear_cache(self) -> None:
        """Clear all cached apps."""
        self.cache.clear()

    def apply_variant(self, module: ModuleType, variant: str | None) -> None:
        """Apply an optional variant configuration to a module if it supports it."""
        configure_variant = _module_attr(module, "configure_variant")
        if not callable(configure_variant):
            return
        try:
            _ = configure_variant(variant)
        except Exception as exc:
            logger.warning("Failed to apply variant %s for %s: %s", variant, module.__name__, exc)


# MARK: Source Extraction


class _HumanMessageExtractor(ast.NodeVisitor):
    """AST visitor to extract HumanMessage content."""

    def __init__(self) -> None:
        self.contents: list[str] = []

    @override
    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
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


# MARK: Global Loader

_loader: AppLoader | None = None


def get_app_loader() -> AppLoader:
    """Get the global app loader instance."""
    global _loader
    if _loader is None:
        _loader = AppLoader()
    return _loader


def init_app_loader(base_path: Path) -> AppLoader:
    """Initialize the global app loader.

    Args:
        base_path: Base path for module imports.

    Returns:
        The initialized loader.
    """
    global _loader
    _loader = AppLoader(base_path)
    return _loader
