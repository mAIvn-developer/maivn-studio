"""Shared private data defaults and schema helpers."""

# pyright: strict

from __future__ import annotations

from pathlib import Path
from typing import Any

from maivn_shared import DataDependency

from maivn_studio.config.models import PrivateDataField

# MARK: Defaults

_default_private_data_cache: dict[str, Any] | None = None


def _find_repo_root() -> Path:
    cwd = Path.cwd()
    for candidate in (cwd, *cwd.parents):
        log_dir = candidate / "logs"
        if not log_dir.exists():
            continue
        if (log_dir / "agent_execution.log").exists() or (
            log_dir / "server_execution.log"
        ).exists():
            return candidate
    return cwd


def _default_log_path() -> str:
    repo_root = _find_repo_root()
    log_dir = repo_root / "logs"
    for filename in ("agent_execution.log", "server_execution.log"):
        candidate = log_dir / filename
        if candidate.exists():
            return str(candidate)
    return str(log_dir / "server_execution.log")


def _build_default_private_data() -> dict[str, Any]:
    return {
        "serial_number": "SN-LPTP-8831",
        "vehicle_id": "VIN12345",
        "sensor_bus_id": "CAN0",
        "manufacturer": "Cote Robotics",
        "account_id": "ACCT-APP-0001",
        "customer_name": "Customer-App",
        "secret_token": "secret-app-token",
        "email": "user@example.com",
        "log_path": _default_log_path(),
    }


def get_default_private_data() -> dict[str, Any]:
    """Return a copy of the default private data values."""
    global _default_private_data_cache
    if _default_private_data_cache is None:
        _default_private_data_cache = _build_default_private_data()
    return _default_private_data_cache.copy()


def reset_default_private_data() -> None:
    """Clear the cached default private data (test seam)."""
    global _default_private_data_cache
    _default_private_data_cache = None


def is_valid_log_path(value: object) -> bool:
    """Validate a log path value for private data."""
    if not isinstance(value, str):
        return False
    if value in ("", ".", "./"):
        return False
    path = Path(value)
    if not path.is_absolute():
        return False
    if path.exists() and not path.is_file():
        return False
    return True


# MARK: Schema Extraction


def extract_private_data_schema(loaded: Any) -> list[PrivateDataField]:
    """Extract private data schema from a loaded app."""
    keys: set[str] = set()
    scopes: list[Any] = []
    scopes.extend(loaded.agents)
    scopes.extend(loaded.swarms)
    for swarm in loaded.swarms:
        if hasattr(swarm, "agents"):
            scopes.extend(list(swarm.agents))

    for scope in scopes:
        if scope is None:
            continue
        try:
            tools = scope.list_tools()
        except Exception:  # noqa: BLE001 - skip scopes whose tools can't be enumerated
            continue

        for tool in tools:
            for dependency in getattr(tool, "dependencies", []) or []:
                if isinstance(dependency, DataDependency) and dependency.data_key:
                    keys.add(dependency.data_key)

    defaults = get_default_private_data()
    return [
        PrivateDataField(
            key=key,
            label=key.replace("_", " ").title(),
            type="string",
            required=True,
            default_value=defaults.get(key, ""),
            description=f"Value for {key}",
        )
        for key in sorted(keys)
    ]
