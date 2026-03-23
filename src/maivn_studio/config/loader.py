"""Configuration loading from JSON files."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .models import StudioConfig

logger = logging.getLogger(__name__)


# MARK: Constants

DEFAULT_CONFIG_FILENAME = "maivn_studio.json"


# MARK: Config Loading


def find_config_file(start_path: Path | None = None) -> Path | None:
    """Find the maivn_studio.json config file.

    Searches in this order:
    1. The start_path if provided
    2. Current working directory
    3. Parent directories up to 3 levels

    Args:
        start_path: Optional starting path to search from.

    Returns:
        Path to the config file if found, None otherwise.
    """
    search_paths: list[Path] = []

    if start_path:
        search_paths.append(start_path)

    cwd = Path.cwd()
    search_paths.append(cwd)

    # Search up to 3 parent levels
    parent = cwd
    for _ in range(3):
        parent = parent.parent
        if parent != parent.parent:  # Not at root
            search_paths.append(parent)

    for path in search_paths:
        config_path = path / DEFAULT_CONFIG_FILENAME
        if config_path.exists():
            return config_path

    return None


def load_config(config_path: Path | None = None) -> StudioConfig:
    """Load studio configuration from a JSON file.

    Args:
        config_path: Path to the config file. If None, searches for one.

    Returns:
        Parsed StudioConfig instance.

    Raises:
        FileNotFoundError: If no config file is found.
        json.JSONDecodeError: If the config file is invalid JSON.
        pydantic.ValidationError: If the config doesn't match the schema.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None:
        logger.warning("No config file found, using defaults")
        return StudioConfig()

    logger.info(f"Loading config from {config_path}")

    with open(config_path, encoding="utf-8") as f:
        data = json.load(f)

    # Remove $schema key if present (JSON Schema reference)
    data.pop("$schema", None)

    return StudioConfig.model_validate(data)


def load_config_from_string(json_string: str) -> StudioConfig:
    """Load studio configuration from a JSON string.

    Args:
        json_string: JSON configuration string.

    Returns:
        Parsed StudioConfig instance.
    """
    data = json.loads(json_string)
    data.pop("$schema", None)
    return StudioConfig.model_validate(data)


# MARK: Global Config State

_current_config: StudioConfig | None = None
_current_config_path: Path | None = None


def get_config_path() -> Path | None:
    """Get the current config path, falling back to discovery if needed."""
    return _current_config_path or find_config_file()


def reload_config() -> StudioConfig:
    """Reload the current Studio configuration from disk."""
    global _current_config, _current_config_path

    config_path = get_config_path()
    _current_config = load_config(config_path)
    _current_config_path = config_path
    return _current_config


def get_config() -> StudioConfig:
    """Get the current global configuration.

    Returns:
        The current StudioConfig instance.
    """
    global _current_config
    if _current_config is None:
        _current_config = load_config()
    return _current_config


def set_config(config: StudioConfig, config_path: Path | None = None) -> None:
    """Set the global configuration.

    Args:
        config: The configuration to set.
        config_path: Optional path to save to.
    """
    global _current_config, _current_config_path
    _current_config = config
    if config_path:
        _current_config_path = config_path


def save_config(config: StudioConfig | None = None) -> None:
    """Save configuration to disk.

    Args:
        config: Optional config to save. If None, uses current config.
    """
    global _current_config, _current_config_path

    if config is None:
        config = _current_config
    if config is None:
        logger.warning("No config to save")
        return

    # Find config path
    config_path = _current_config_path or find_config_file()
    if config_path is None:
        logger.warning("No config path found to save to")
        return

    # Convert to dict and save
    data = config.model_dump(mode="json")
    data["$schema"] = "https://maivn.dev/schema/studio.json"

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Saved config to {config_path}")
