"""App registry for managing discovered and configured apps."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Literal

from maivn_studio.config.models import AppConfig, StudioConfig

from .scanner import discover_all_apps

logger = logging.getLogger(__name__)

AppSource = Literal["configured", "discovered"]


# MARK: App Registry


class AppRegistry:
    """Central registry for all available apps.

    Combines explicitly configured apps with auto-discovered apps.
    Explicit configs take precedence over discovered ones.
    """

    def __init__(self) -> None:
        self._apps: dict[str, AppConfig] = {}
        self._by_category: dict[str, list[str]] = {}
        self._sources: dict[str, AppSource] = {}

    @property
    def apps(self) -> list[AppConfig]:
        """Get all registered apps."""
        return list(self._apps.values())

    @property
    def categories(self) -> list[str]:
        """Get all unique categories."""
        return list(self._by_category.keys())

    def get(self, app_id: str) -> AppConfig | None:
        """Get an app by ID."""
        return self._apps.get(app_id)

    def get_source(self, app_id: str) -> AppSource:
        """Get the registration source for an app."""
        return self._sources.get(app_id, "configured")

    def get_by_category(self, category: str) -> list[AppConfig]:
        """Get all apps in a category."""
        app_ids = self._by_category.get(category, [])
        return [self._apps[aid] for aid in app_ids if aid in self._apps]

    def register(self, app: AppConfig, source: AppSource = "configured") -> None:
        """Register an app.

        Args:
            app: The app configuration to register.
            source: Whether the app came from config or auto-discovery.
        """
        previous = self._apps.get(app.id)
        if previous is not None and previous.category != app.category:
            previous_ids = self._by_category.get(previous.category, [])
            self._by_category[previous.category] = [aid for aid in previous_ids if aid != app.id]
            if not self._by_category[previous.category]:
                self._by_category.pop(previous.category, None)

        self._apps[app.id] = app
        self._sources[app.id] = source

        # Update category index
        if app.category not in self._by_category:
            self._by_category[app.category] = []
        if app.id not in self._by_category[app.category]:
            self._by_category[app.category].append(app.id)

        logger.debug(f"Registered app: {app.id} ({app.category}, {source})")

    def register_all(
        self,
        apps: list[AppConfig],
        source: AppSource = "configured",
    ) -> None:
        """Register multiple apps.

        Args:
            apps: List of app configurations to register.
            source: Whether the apps came from config or auto-discovery.
        """
        for app in apps:
            self.register(app, source)

    def clear(self) -> None:
        """Clear all registered apps."""
        self._apps.clear()
        self._by_category.clear()
        self._sources.clear()

    def _remove_app(self, app_id: str) -> None:
        existing = self._apps.pop(app_id, None)
        self._sources.pop(app_id, None)
        if existing is None:
            return

        category_ids = self._by_category.get(existing.category, [])
        self._by_category[existing.category] = [aid for aid in category_ids if aid != app_id]
        if not self._by_category[existing.category]:
            self._by_category.pop(existing.category, None)

    @staticmethod
    def _module_key(module: str) -> str:
        return module.strip().lower()

    def _merge_apps(
        self,
        discovered: list[AppConfig],
        configured: list[AppConfig],
    ) -> list[tuple[AppConfig, AppSource]]:
        merged: dict[str, tuple[AppConfig, AppSource]] = {}
        discovered_by_module: dict[str, str] = {}

        def upsert_discovered(app: AppConfig) -> None:
            module_key = self._module_key(app.module)
            duplicate_id = discovered_by_module.get(module_key)
            if duplicate_id is not None and duplicate_id != app.id:
                merged.pop(duplicate_id, None)

            merged[app.id] = (app.model_copy(deep=True), "discovered")
            discovered_by_module[module_key] = app.id

        def upsert_configured(app: AppConfig) -> None:
            module_key = self._module_key(app.module)
            duplicate_id = discovered_by_module.pop(module_key, None)
            if duplicate_id is not None:
                merged.pop(duplicate_id, None)

            merged[app.id] = (app.model_copy(deep=True), "configured")

        for app in discovered:
            upsert_discovered(app)

        for app in configured:
            upsert_configured(app)

        return list(merged.values())

    def load_from_config(self, config: StudioConfig, base_path: Path) -> None:
        """Load apps from a studio configuration.

        This merges:
        1. Auto-discovered apps from discovery.paths
        2. Explicitly configured apps (override discovered)

        Args:
            config: The studio configuration.
            base_path: Base path for discovery resolution.
        """
        self.clear()

        discovered: list[AppConfig] = []

        # First, auto-discover apps
        if config.discovery.paths:
            discovered = discover_all_apps(
                base_path=base_path,
                discovery_paths=config.discovery.paths,
                exclude_patterns=config.discovery.exclude,
            )
            logger.info(f"Auto-discovered {len(discovered)} apps")

        merged = self._merge_apps(discovered, config.apps)
        for app, source in merged:
            self.register(app, source)

        configured_count = sum(1 for _, source in merged if source == "configured")
        discovered_count = sum(1 for _, source in merged if source == "discovered")

        logger.info(
            "Registry loaded: %s apps in %s categories (%s configured, %s discovered)",
            len(self._apps),
            len(self._by_category),
            configured_count,
            discovered_count,
        )

    def to_dict(self) -> dict[str, list[dict]]:
        """Export registry as a dictionary grouped by category."""
        result: dict[str, list[dict]] = {}
        for category in sorted(self._by_category.keys()):
            apps = self.get_by_category(category)
            result[category] = [a.model_dump() for a in apps]
        return result


# MARK: Global Registry

_registry: AppRegistry | None = None


def get_registry() -> AppRegistry:
    """Get the global app registry instance."""
    global _registry
    if _registry is None:
        _registry = AppRegistry()
    return _registry


def init_registry(config: StudioConfig, base_path: Path) -> AppRegistry:
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
