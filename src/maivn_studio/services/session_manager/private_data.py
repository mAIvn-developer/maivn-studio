"""Private data helpers for session management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from maivn_shared import DataDependency

from maivn_studio.private_data import get_default_private_data, is_valid_log_path

from ..demo_loader.models import LoadedDemo

logger = logging.getLogger(__name__)


# MARK: Private Data Functions


def apply_private_data(
    loaded: LoadedDemo,
    user_private_data: dict[str, Any] | None = None,
) -> None:
    """Apply private data to loaded demo, merging user values with defaults.

    Args:
        loaded: The loaded demo.
        user_private_data: User-provided private data values.
    """
    # Merge user-provided values with defaults (user values take precedence)
    default_private_data = get_default_private_data()
    sanitized_user_private_data: dict[str, Any] = {}
    if user_private_data:
        sanitized_user_private_data = dict(user_private_data)
        if "log_path" in sanitized_user_private_data and not is_valid_log_path(
            sanitized_user_private_data.get("log_path")
        ):
            sanitized_user_private_data.pop("log_path", None)
        default_private_data.update(sanitized_user_private_data)

    explicit_private_data = sanitized_user_private_data if user_private_data else {}

    scopes: list[Any] = []
    scopes.extend(loaded.agents)
    scopes.extend(loaded.swarms)
    for swarm in loaded.swarms:
        if hasattr(swarm, "agents"):
            scopes.extend(list(swarm.agents))

    seen: set[int] = set()
    for scope in scopes:
        if scope is None:
            continue
        scope_id = id(scope)
        if scope_id in seen:
            continue
        seen.add(scope_id)

        applied_keys = _apply_explicit_private_data(scope, explicit_private_data)
        if applied_keys:
            scope_name = getattr(scope, "name", scope.__class__.__name__)
            logger.info(
                "Applied explicit private_data to %s: %s",
                scope_name,
                ", ".join(applied_keys),
            )

        missing = _fill_missing_private_data(scope, default_private_data)
        if missing:
            scope_name = getattr(scope, "name", scope.__class__.__name__)
            logger.info(
                "Filled private_data defaults for %s: %s",
                scope_name,
                ", ".join(missing),
            )


def _apply_explicit_private_data(
    scope: Any,
    private_data: dict[str, Any],
) -> list[str]:
    """Apply explicit session private_data to a scope even without DataDependency declarations."""
    if not private_data:
        return []

    current_private_data = dict(getattr(scope, "private_data", {}) or {})
    applied_keys: list[str] = []

    for key, value in private_data.items():
        if current_private_data.get(key) == value:
            continue
        current_private_data[key] = value
        applied_keys.append(key)

    if applied_keys:
        scope.private_data = current_private_data

    return sorted(applied_keys)


def _fill_missing_private_data(
    scope: Any,
    defaults: dict[str, Any],
) -> list[str]:
    """Fill missing private data keys on a scope with defaults.

    Args:
        scope: An agent or swarm instance.
        defaults: Default private data values.

    Returns:
        List of keys that were filled.
    """
    required_keys = _collect_private_data_keys(scope)
    if not required_keys:
        return []

    private_data = dict(getattr(scope, "private_data", {}) or {})
    missing: list[str] = []
    for key in sorted(required_keys):
        current_value = private_data.get(key)
        # Fill if missing OR if it's an invalid path (like '.' or relative paths)
        needs_default = current_value is None or key not in private_data
        if key == "log_path" and current_value:
            # Validate log_path - override if it's '.' or doesn't look like a valid path
            current_path = Path(str(current_value))
            if current_value in (".", "./") or (
                not current_path.is_absolute() and not current_path.exists()
            ):
                needs_default = True
                logger.warning(f'Overriding invalid log_path "{current_value}" with studio default')
            elif current_path.exists() and not current_path.is_file():
                needs_default = True
                logger.warning(f'Overriding invalid log_path "{current_value}" with studio default')
        if needs_default:
            private_data[key] = defaults.get(key, f"demo_{key}")
            missing.append(key)

    if missing:
        scope.private_data = private_data

    return missing


def _collect_private_data_keys(scope: Any) -> set[str]:
    """Collect all private data keys required by a scope's tools.

    Args:
        scope: An agent or swarm instance.

    Returns:
        Set of required data keys.
    """
    try:
        tools = scope.list_tools()
    except Exception:
        return set()

    keys: set[str] = set()
    for tool in tools:
        for dependency in getattr(tool, "dependencies", []) or []:
            if isinstance(dependency, DataDependency) and dependency.data_key:
                keys.add(dependency.data_key)

    return keys
