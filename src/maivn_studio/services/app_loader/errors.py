"""App module import errors surfaced by Studio."""

# pyright: strict
from __future__ import annotations

import re

# MARK: Helpers


_MISSING_MODULE_RE = re.compile(r"No module named '([^']+)'")


def extract_missing_module(error: BaseException) -> str | None:
    """Return the missing top-level module name from an import failure, if known."""
    current: BaseException | None = error
    while current is not None:
        name = getattr(current, "name", None)
        if isinstance(name, str) and name:
            return name
        match = _MISSING_MODULE_RE.search(str(current))
        if match:
            return match.group(1)
        current = current.__cause__
    return None


def format_app_load_error(app_module: str, error: BaseException) -> str:
    """Build a user-facing message for a failed app import."""
    missing_module = extract_missing_module(error)
    if missing_module:
        return (
            f"App module '{app_module}' could not be loaded because "
            f"'{missing_module}' is not installed in this Studio environment. "
            f"Install the Python package that provides that module, then restart Studio."
        )
    return (
        f"App module '{app_module}' could not be loaded: {error}. "
        f"Verify the module path and that its dependencies are installed "
        f"in this Studio environment."
    )


# MARK: App Load Error


class AppLoadError(ImportError):
    """Raised when Studio cannot import a configured app module."""

    def __init__(self, app_module: str, cause: BaseException) -> None:
        self.app_module = app_module
        self.missing_module = extract_missing_module(cause)
        super().__init__(format_app_load_error(app_module, cause))
        self.__cause__ = cause
