# pyright: strict

from __future__ import annotations

from maivn_studio.config.loader import reset_config


def pytest_runtest_setup() -> None:
    reset_config()


def pytest_runtest_teardown() -> None:
    reset_config()
