"""Demo registry for managing discovered and configured demos."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from maivn_studio.config.models import DemoConfig, StudioConfig

from .scanner import discover_all_demos

logger = logging.getLogger(__name__)

DemoSource = Literal["configured", "discovered"]


# MARK: Demo Registry


class DemoRegistry:
    """Central registry for all available demos.

    Combines explicitly configured demos with auto-discovered demos.
    Explicit configs take precedence over discovered ones.
    """

    def __init__(self) -> None:
        self._demos: dict[str, DemoConfig] = {}
        self._by_category: dict[str, list[str]] = {}
        self._sources: dict[str, DemoSource] = {}

    @property
    def demos(self) -> list[DemoConfig]:
        """Get all registered demos."""
        return list(self._demos.values())

    @property
    def categories(self) -> list[str]:
        """Get all unique categories."""
        return list(self._by_category.keys())

    def get(self, demo_id: str) -> DemoConfig | None:
        """Get a demo by ID."""
        return self._demos.get(demo_id)

    def get_source(self, demo_id: str) -> DemoSource:
        """Get the registration source for a demo."""
        return self._sources.get(demo_id, "configured")

    def get_by_category(self, category: str) -> list[DemoConfig]:
        """Get all demos in a category."""
        demo_ids = self._by_category.get(category, [])
        return [self._demos[did] for did in demo_ids if did in self._demos]

    def register(self, demo: DemoConfig, source: DemoSource = "configured") -> None:
        """Register a demo.

        Args:
            demo: The demo configuration to register.
            source: Whether the demo came from config or auto-discovery.
        """
        previous = self._demos.get(demo.id)
        if previous is not None and previous.category != demo.category:
            previous_ids = self._by_category.get(previous.category, [])
            self._by_category[previous.category] = [did for did in previous_ids if did != demo.id]
            if not self._by_category[previous.category]:
                self._by_category.pop(previous.category, None)

        self._demos[demo.id] = demo
        self._sources[demo.id] = source

        # Update category index
        if demo.category not in self._by_category:
            self._by_category[demo.category] = []
        if demo.id not in self._by_category[demo.category]:
            self._by_category[demo.category].append(demo.id)

        logger.debug(f"Registered demo: {demo.id} ({demo.category}, {source})")

    def register_all(
        self,
        demos: list[DemoConfig],
        source: DemoSource = "configured",
    ) -> None:
        """Register multiple demos.

        Args:
            demos: List of demo configurations to register.
            source: Whether the demos came from config or auto-discovery.
        """
        for demo in demos:
            self.register(demo, source)

    def clear(self) -> None:
        """Clear all registered demos."""
        self._demos.clear()
        self._by_category.clear()
        self._sources.clear()

    def _remove_demo(self, demo_id: str) -> None:
        existing = self._demos.pop(demo_id, None)
        self._sources.pop(demo_id, None)
        if existing is None:
            return

        category_ids = self._by_category.get(existing.category, [])
        self._by_category[existing.category] = [did for did in category_ids if did != demo_id]
        if not self._by_category[existing.category]:
            self._by_category.pop(existing.category, None)

    @staticmethod
    def _module_key(module: str) -> str:
        return module.strip().lower()

    def _merge_demos(
        self,
        discovered: list[DemoConfig],
        configured: list[DemoConfig],
    ) -> list[tuple[DemoConfig, DemoSource]]:
        merged: dict[str, tuple[DemoConfig, DemoSource]] = {}
        discovered_by_module: dict[str, str] = {}

        def upsert_discovered(demo: DemoConfig) -> None:
            module_key = self._module_key(demo.module)
            duplicate_id = discovered_by_module.get(module_key)
            if duplicate_id is not None and duplicate_id != demo.id:
                merged.pop(duplicate_id, None)

            merged[demo.id] = (demo.model_copy(deep=True), "discovered")
            discovered_by_module[module_key] = demo.id

        def upsert_configured(demo: DemoConfig) -> None:
            module_key = self._module_key(demo.module)
            duplicate_id = discovered_by_module.pop(module_key, None)
            if duplicate_id is not None:
                merged.pop(duplicate_id, None)

            merged[demo.id] = (demo.model_copy(deep=True), "configured")

        for demo in discovered:
            upsert_discovered(demo)

        for demo in configured:
            upsert_configured(demo)

        return list(merged.values())

    def load_from_config(self, config: StudioConfig, base_path: Path) -> None:
        """Load demos from a studio configuration.

        This merges:
        1. Auto-discovered demos from discovery.paths
        2. Explicitly configured demos (override discovered)

        Args:
            config: The studio configuration.
            base_path: Base path for discovery resolution.
        """
        self.clear()

        discovered: list[DemoConfig] = []

        # First, auto-discover demos
        if config.discovery.paths:
            discovered = discover_all_demos(
                base_path=base_path,
                discovery_paths=config.discovery.paths,
                exclude_patterns=config.discovery.exclude,
            )
            logger.info(f"Auto-discovered {len(discovered)} demos")

        merged = self._merge_demos(discovered, config.demos)
        for demo, source in merged:
            self.register(demo, source)

        configured_count = sum(1 for _, source in merged if source == "configured")
        discovered_count = sum(1 for _, source in merged if source == "discovered")

        logger.info(
            "Registry loaded: %s demos in %s categories (%s configured, %s discovered)",
            len(self._demos),
            len(self._by_category),
            configured_count,
            discovered_count,
        )

    def to_dict(self) -> dict[str, list[dict]]:
        """Export registry as a dictionary grouped by category."""
        result: dict[str, list[dict]] = {}
        for category in sorted(self._by_category.keys()):
            demos = self.get_by_category(category)
            result[category] = [d.model_dump() for d in demos]
        return result


# MARK: Global Registry

_registry: DemoRegistry | None = None


def get_registry() -> DemoRegistry:
    """Get the global demo registry instance."""
    global _registry
    if _registry is None:
        _registry = DemoRegistry()
    return _registry


def init_registry(config: StudioConfig, base_path: Path) -> DemoRegistry:
    """Initialize the global registry from config.

    Args:
        config: The studio configuration.
        base_path: Base path for discovery resolution.

    Returns:
        The initialized registry.
    """
    registry = get_registry()
    registry.load_from_config(config, base_path)
    return registry
