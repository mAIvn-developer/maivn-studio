from __future__ import annotations

import maivn_studio.config.loader as config_loader


def pytest_runtest_setup() -> None:
    config_loader._current_config = None
    config_loader._current_config_path = None


def pytest_runtest_teardown() -> None:
    config_loader._current_config = None
    config_loader._current_config_path = None
