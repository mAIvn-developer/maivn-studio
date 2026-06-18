"""Tests for app loader import error helpers."""

# pyright: strict
from __future__ import annotations

from maivn_studio.services.app_loader.errors import (
    AppLoadError,
    extract_missing_module,
    format_app_load_error,
)


def test_extract_missing_module_from_module_not_found_error() -> None:
    error = ModuleNotFoundError("No module named 'maivn_tools'")
    assert extract_missing_module(error) == "maivn_tools"


def test_format_app_load_error_includes_missing_module_guidance() -> None:
    message = format_app_load_error(
        "demos.toolsets.maivn_tools_gmail_demo",
        ModuleNotFoundError("No module named 'maivn_tools'"),
    )
    assert "maivn_tools" in message
    assert "demos.toolsets.maivn_tools_gmail_demo" in message
    assert "Install the Python package" in message


def test_app_load_error_preserves_missing_module() -> None:
    error = AppLoadError(
        "demos.toolsets.maivn_tools_gmail_demo",
        ModuleNotFoundError("No module named 'maivn_tools'"),
    )
    assert error.missing_module == "maivn_tools"
    assert "maivn_tools" in str(error)
