"""Demo discovery and scanning."""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from maivn_studio.config.models import DemoConfig, DemoVariant

logger = logging.getLogger(__name__)


# MARK: AST Analysis


class DemoModuleAnalyzer(ast.NodeVisitor):
    """AST visitor to extract demo metadata from a Python module.

    Focuses on finding module-level Agent and Swarm instances, as well as
    pre-defined prompts (DEMO_PROMPTS, DEFAULT_PROMPT, messages).
    """

    def __init__(self) -> None:
        self.agents: list[str] = []
        self.swarms: list[str] = []
        self.has_demo_prompts: bool = False
        self.has_default_prompt: bool = False
        self.has_messages: bool = False
        self.argparse_args: list[dict[str, Any]] = []
        self.docstring: str | None = None

    def visit_Module(self, node: ast.Module) -> None:
        """Extract module docstring."""
        if node.body and isinstance(node.body[0], ast.Expr):
            if isinstance(node.body[0].value, ast.Constant):
                value = node.body[0].value.value
                if isinstance(value, str):
                    self.docstring = value
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Detect Agent, Swarm, and prompt assignments at module level."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            var_name = node.targets[0].id

            # Check for Agent/Swarm instantiation
            if isinstance(node.value, ast.Call):
                func = node.value.func
                if isinstance(func, ast.Name):
                    if func.id == "Agent":
                        self.agents.append(var_name)
                    elif func.id == "Swarm":
                        self.swarms.append(var_name)

            # Check for prompt definitions
            if var_name == "DEMO_PROMPTS":
                self.has_demo_prompts = True
            elif var_name == "DEFAULT_PROMPT":
                self.has_default_prompt = True
            elif var_name == "messages":
                self.has_messages = True

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Look for argparse arguments for variant discovery."""
        # Look for argparse arguments in any function (for variant discovery)
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Attribute):
                    if child.func.attr == "add_argument":
                        self._extract_argparse_arg(child)

        self.generic_visit(node)

    def _extract_argparse_arg(self, call: ast.Call) -> None:
        """Extract argparse argument info from add_argument call."""
        if not call.args:
            return

        first_arg = call.args[0]
        if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
            arg_name = first_arg.value
            if arg_name.startswith("--"):
                arg_info: dict[str, Any] = {"name": arg_name}

                # Extract help text
                for keyword in call.keywords:
                    if keyword.arg == "help" and isinstance(keyword.value, ast.Constant):
                        arg_info["help"] = keyword.value.value
                    elif keyword.arg == "action" and isinstance(keyword.value, ast.Constant):
                        arg_info["action"] = keyword.value.value

                self.argparse_args.append(arg_info)

    @property
    def has_executor(self) -> bool:
        """Check if module has any executable Agent or Swarm."""
        return bool(self.agents or self.swarms)

    @property
    def has_prompts(self) -> bool:
        """Check if module has any pre-defined prompts."""
        return self.has_demo_prompts or self.has_default_prompt or self.has_messages


def analyze_module(file_path: Path) -> DemoModuleAnalyzer:
    """Analyze a Python module file for demo metadata.

    Args:
        file_path: Path to the Python file.

    Returns:
        DemoModuleAnalyzer with extracted metadata.
    """
    with open(file_path, encoding="utf-8") as f:
        source = f.read()

    tree = ast.parse(source)
    analyzer = DemoModuleAnalyzer()
    analyzer.visit(tree)
    return analyzer


# MARK: Demo Discovery


def discover_demos_in_path(
    base_path: Path,
    search_path: str,
    exclude_patterns: list[str],
) -> list[DemoConfig]:
    """Discover demo modules in a given path.

    Args:
        base_path: The base path to resolve relative paths from.
        search_path: Relative path to search for demos.
        exclude_patterns: Patterns to exclude from discovery.

    Returns:
        List of discovered DemoConfig instances.
    """
    demos: list[DemoConfig] = []
    full_path = base_path / search_path

    if not full_path.exists():
        logger.warning(f"Discovery path does not exist: {full_path}")
        return demos

    for py_file in full_path.rglob("*.py"):
        # Skip excluded patterns
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue

        # Skip __init__.py and test files
        if py_file.name.startswith("__") or py_file.name.startswith("test_"):
            continue

        try:
            demo = build_demo_config(py_file, base_path, search_path)
            if demo:
                demos.append(demo)
                logger.debug(f"Discovered demo: {demo.id}")
        except Exception as e:
            logger.warning(f"Failed to analyze {py_file}: {e}")

    return demos


def _build_demo_config_from_analyzer(
    analyzer: DemoModuleAnalyzer,
    file_path: Path,
    base_path: Path,
    search_path: str,
) -> DemoConfig:
    """Build a DemoConfig from an analyzed module."""
    # Build module path
    relative_path = file_path.relative_to(base_path)
    module_parts = list(relative_path.with_suffix("").parts)
    module_path = ".".join(module_parts)

    # Generate ID from filename
    demo_id = file_path.stem.replace("_demo", "").replace("_", "-")

    # Determine category from path
    category = "uncategorized"
    path_parts = search_path.split("/")
    if len(path_parts) > 1:
        category = path_parts[-1]

    # Generate name from filename
    name = file_path.stem.replace("_", " ").title().replace(" Demo", "")

    # Extract description from docstring
    description = ""
    if analyzer.docstring:
        # Take first line of docstring
        lines = analyzer.docstring.strip().split("\n")
        description = lines[0].strip().strip("#").strip()

    # Build variants from argparse args (kept for CLI compatibility)
    variants: dict[str, DemoVariant] = {}
    for arg in analyzer.argparse_args:
        arg_name = arg["name"].lstrip("-")
        variant_id = arg_name.replace("_", "-")
        variants[variant_id] = DemoVariant(
            args=[arg["name"]],
            description=arg.get("help", f"Run with {arg_name}"),
        )

    # Build tags including executor types and prompt info
    tags: list[str] = []
    if category != "uncategorized":
        tags.append(category)
    if analyzer.swarms:
        tags.append("swarm")
    if analyzer.agents:
        tags.append("agent")
    if analyzer.has_prompts:
        tags.append("has-prompts")

    return DemoConfig(
        id=demo_id,
        name=name,
        description=description,
        module=module_path,
        category=category,
        tags=tags,
        variants=variants,
    )


def build_demo_config(
    file_path: Path,
    base_path: Path,
    search_path: str,
) -> DemoConfig | None:
    """Create a DemoConfig from a Python file.

    A valid demo module must have at least one module-level Agent or Swarm
    instance. Entry point functions are no longer required.

    Args:
        file_path: Path to the Python file.
        base_path: Base path for module resolution.
        search_path: The search path this file was found in.

    Returns:
        DemoConfig if the file is a valid demo, None otherwise.
    """
    resolved_base_path = base_path.resolve()
    resolved_file_path = file_path.resolve()
    try:
        resolved_file_path.relative_to(resolved_base_path)
    except ValueError:
        return None

    analyzer = analyze_module(resolved_file_path)

    # Must have at least one agent or swarm at module level
    if not analyzer.has_executor:
        return None

    return _build_demo_config_from_analyzer(
        analyzer,
        resolved_file_path,
        resolved_base_path,
        search_path,
    )


def discover_all_demos(
    base_path: Path,
    discovery_paths: list[str],
    exclude_patterns: list[str],
) -> list[DemoConfig]:
    """Discover all demos from configured paths.

    Args:
        base_path: Base path to resolve relative paths from.
        discovery_paths: List of relative paths to search.
        exclude_patterns: Patterns to exclude from discovery.

    Returns:
        List of all discovered DemoConfig instances.
    """
    all_demos: list[DemoConfig] = []

    for search_path in discovery_paths:
        demos = discover_demos_in_path(base_path, search_path, exclude_patterns)
        all_demos.extend(demos)

    logger.info(f"Discovered {len(all_demos)} demos from {len(discovery_paths)} paths")
    return all_demos


# MARK: Repo Scan


DEFAULT_SCAN_EXCLUDES = [
    ".git",
    ".venv",
    ".svelte-kit",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
]


def scan_repo_for_demos(
    base_path: Path,
    discovery_paths: list[str],
    exclude_patterns: list[str],
) -> list[dict[str, Any]]:
    """Scan repo paths for demo candidates and return metadata for UI selection."""
    results: list[dict[str, Any]] = []
    scan_excludes = list({*exclude_patterns, *DEFAULT_SCAN_EXCLUDES})
    resolved_base_path = base_path.resolve()

    for search_path in discovery_paths:
        full_path = (base_path / search_path).resolve()
        try:
            full_path.relative_to(resolved_base_path)
        except ValueError:
            continue
        if not full_path.exists():
            logger.warning(f"Discovery path does not exist: {full_path}")
            continue

        for py_file in full_path.rglob("*.py"):
            if any(pattern in str(py_file) for pattern in scan_excludes):
                continue
            if py_file.name.startswith("__") or py_file.name.startswith("test_"):
                continue

            try:
                analyzer = analyze_module(py_file)
            except Exception as exc:
                logger.warning(f"Failed to analyze {py_file}: {exc}")
                continue

            if not analyzer.has_executor:
                continue

            demo = _build_demo_config_from_analyzer(
                analyzer,
                py_file,
                resolved_base_path,
                search_path,
            )
            results.append(
                {
                    "id": demo.id,
                    "name": demo.name,
                    "description": demo.description,
                    "module": demo.module,
                    "category": demo.category,
                    "tags": demo.tags,
                    "file_path": str(py_file.relative_to(base_path)),
                    "discovery_path": search_path,
                    "agents": sorted(analyzer.agents),
                    "swarms": sorted(analyzer.swarms),
                }
            )

    return results
