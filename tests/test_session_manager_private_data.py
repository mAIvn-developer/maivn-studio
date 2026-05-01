"""Tests for services/session_manager/private_data.py."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from maivn_shared import DataDependency

from maivn_studio.services.session_manager.private_data import (
    _collect_private_data_keys,
    _fill_missing_private_data,
    apply_private_data,
)

# MARK: Helpers


def _make_tool(data_keys: list[str]) -> SimpleNamespace:
    """Create a mock tool with DataDependency entries."""
    deps = [DataDependency(arg_name=k, data_key=k) for k in data_keys]
    return SimpleNamespace(dependencies=deps)


def _make_scope(
    name: str = "test_scope",
    tools: list[Any] | None = None,
    private_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mock agent/swarm scope."""
    scope = MagicMock()
    scope.name = name
    scope.private_data = dict(private_data) if private_data else {}
    scope.list_tools.return_value = tools or []
    return scope


def _make_loaded(
    agents: list[Any] | None = None,
    swarms: list[Any] | None = None,
) -> Any:
    """Create a mock LoadedApp."""
    return SimpleNamespace(
        agents=agents or [],
        swarms=swarms or [],
    )


# MARK: apply_private_data


class TestApplyPrivateData:
    """Tests for apply_private_data()."""

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    def test_merges_user_data_with_defaults(self, mock_defaults: MagicMock) -> None:
        mock_defaults.return_value = {"key_a": "default_a", "key_b": "default_b"}
        agent = _make_scope(tools=[_make_tool(["key_a", "key_b"])])
        loaded = _make_loaded(agents=[agent])

        apply_private_data(loaded, user_private_data={"key_a": "user_a"})

        pd = agent.private_data
        assert pd["key_a"] == "user_a"
        assert pd["key_b"] == "default_b"

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    @patch("maivn_studio.services.session_manager.private_data.is_valid_log_path")
    def test_validates_log_path_valid(
        self, mock_valid: MagicMock, mock_defaults: MagicMock
    ) -> None:
        mock_defaults.return_value = {"log_path": "/default/log.txt"}
        mock_valid.return_value = True
        agent = _make_scope(tools=[_make_tool(["log_path"])])
        loaded = _make_loaded(agents=[agent])

        apply_private_data(loaded, user_private_data={"log_path": "/valid/path.log"})

        # User value kept because is_valid_log_path returned True
        assert agent.private_data["log_path"] == "/valid/path.log"

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    @patch("maivn_studio.services.session_manager.private_data.is_valid_log_path")
    def test_strips_invalid_log_path(self, mock_valid: MagicMock, mock_defaults: MagicMock) -> None:
        mock_defaults.return_value = {"log_path": "/default/log.txt"}
        mock_valid.return_value = False
        agent = _make_scope(tools=[_make_tool(["log_path"])])
        loaded = _make_loaded(agents=[agent])

        apply_private_data(loaded, user_private_data={"log_path": "."})

        # Invalid log_path removed; default used instead
        assert agent.private_data["log_path"] == "/default/log.txt"

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    def test_fills_missing_keys_from_defaults(self, mock_defaults: MagicMock) -> None:
        mock_defaults.return_value = {"secret_token": "tok123", "email": "a@b.com"}
        agent = _make_scope(tools=[_make_tool(["secret_token", "email"])])
        loaded = _make_loaded(agents=[agent])

        apply_private_data(loaded, user_private_data=None)

        assert agent.private_data["secret_token"] == "tok123"
        assert agent.private_data["email"] == "a@b.com"

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    def test_applies_explicit_private_data_without_declared_dependencies(
        self, mock_defaults: MagicMock
    ) -> None:
        mock_defaults.return_value = {"secret_token": "default-token"}
        agent = _make_scope(tools=[])
        loaded = _make_loaded(agents=[agent])

        apply_private_data(
            loaded,
            user_private_data={
                "email": "studio-repl-private@maivn.dev",
                "dataset_id": "REPL-DATASET-5914",
            },
        )

        assert agent.private_data["email"] == "studio-repl-private@maivn.dev"
        assert agent.private_data["dataset_id"] == "REPL-DATASET-5914"
        assert "secret_token" not in agent.private_data

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    def test_explicit_private_data_overrides_existing_scope_values(
        self, mock_defaults: MagicMock
    ) -> None:
        mock_defaults.return_value = {"secret_token": "default-token"}
        agent = _make_scope(
            tools=[],
            private_data={"email": "existing@example.com", "secret_token": "embedded-token"},
        )
        loaded = _make_loaded(agents=[agent])

        apply_private_data(
            loaded,
            user_private_data={"email": "studio-think-private@maivn.dev"},
        )

        assert agent.private_data["email"] == "studio-think-private@maivn.dev"
        assert agent.private_data["secret_token"] == "embedded-token"

    @patch("maivn_studio.services.session_manager.private_data.get_default_private_data")
    def test_includes_swarm_member_agents(self, mock_defaults: MagicMock) -> None:
        mock_defaults.return_value = {"api_key": "key123"}
        member = _make_scope(name="member_agent", tools=[_make_tool(["api_key"])])
        swarm = _make_scope(name="test_swarm", tools=[])
        swarm.agents = [member]
        loaded = _make_loaded(swarms=[swarm])

        apply_private_data(loaded)

        assert member.private_data["api_key"] == "key123"


# MARK: _fill_missing_private_data


class TestFillMissingPrivateData:
    """Tests for _fill_missing_private_data()."""

    def test_fills_missing_keys(self) -> None:
        scope = _make_scope(tools=[_make_tool(["key_a", "key_b"])])
        defaults = {"key_a": "val_a", "key_b": "val_b"}

        filled = _fill_missing_private_data(scope, defaults)

        assert sorted(filled) == ["key_a", "key_b"]
        assert scope.private_data["key_a"] == "val_a"
        assert scope.private_data["key_b"] == "val_b"

    def test_skips_already_filled_keys(self) -> None:
        scope = _make_scope(
            tools=[_make_tool(["key_a", "key_b"])],
            private_data={"key_a": "existing"},
        )
        defaults = {"key_a": "default_a", "key_b": "default_b"}

        filled = _fill_missing_private_data(scope, defaults)

        assert filled == ["key_b"]
        assert scope.private_data["key_a"] == "existing"
        assert scope.private_data["key_b"] == "default_b"

    def test_returns_empty_when_no_required_keys(self) -> None:
        scope = _make_scope(tools=[])
        filled = _fill_missing_private_data(scope, {"key_a": "val"})
        assert filled == []

    def test_falls_back_to_app_prefix_when_no_default(self) -> None:
        scope = _make_scope(tools=[_make_tool(["exotic_key"])])
        filled = _fill_missing_private_data(scope, {})

        assert filled == ["exotic_key"]
        assert scope.private_data["exotic_key"] == "app_exotic_key"

    def test_overrides_dot_log_path(self) -> None:
        scope = _make_scope(
            tools=[_make_tool(["log_path"])],
            private_data={"log_path": "."},
        )
        defaults = {"log_path": "/studio/logs/exec.log"}

        filled = _fill_missing_private_data(scope, defaults)

        assert "log_path" in filled
        assert scope.private_data["log_path"] == "/studio/logs/exec.log"

    def test_overrides_dot_slash_log_path(self) -> None:
        scope = _make_scope(
            tools=[_make_tool(["log_path"])],
            private_data={"log_path": "./"},
        )
        defaults = {"log_path": "/studio/logs/exec.log"}

        filled = _fill_missing_private_data(scope, defaults)

        assert "log_path" in filled

    def test_overrides_relative_log_path(self) -> None:
        scope = _make_scope(
            tools=[_make_tool(["log_path"])],
            private_data={"log_path": "some/relative/path.log"},
        )
        defaults = {"log_path": "/studio/logs/exec.log"}

        filled = _fill_missing_private_data(scope, defaults)

        # Relative path that doesn't exist -> overridden
        assert "log_path" in filled

    @patch("maivn_studio.services.session_manager.private_data.Path")
    def test_overrides_non_file_log_path(self, mock_path_cls: MagicMock) -> None:
        """A log_path pointing to an existing directory should be overridden."""
        mock_path_inst = MagicMock()
        mock_path_inst.is_absolute.return_value = True
        mock_path_inst.exists.return_value = True
        mock_path_inst.is_file.return_value = False
        mock_path_cls.return_value = mock_path_inst

        scope = _make_scope(
            tools=[_make_tool(["log_path"])],
            private_data={"log_path": "/some/directory"},
        )
        defaults = {"log_path": "/studio/logs/exec.log"}

        filled = _fill_missing_private_data(scope, defaults)

        assert "log_path" in filled


# MARK: _collect_private_data_keys


class TestCollectPrivateDataKeys:
    """Tests for _collect_private_data_keys()."""

    def test_collects_data_keys_from_tools(self) -> None:
        scope = _make_scope(
            tools=[
                _make_tool(["key_a"]),
                _make_tool(["key_b", "key_c"]),
            ]
        )

        keys = _collect_private_data_keys(scope)

        assert keys == {"key_a", "key_b", "key_c"}

    def test_handles_scope_with_no_tools(self) -> None:
        scope = _make_scope(tools=[])
        keys = _collect_private_data_keys(scope)
        assert keys == set()

    def test_handles_exception_from_list_tools(self) -> None:
        scope = MagicMock()
        scope.list_tools.side_effect = RuntimeError("boom")

        keys = _collect_private_data_keys(scope)

        assert keys == set()

    def test_ignores_tools_without_dependencies(self) -> None:
        tool = SimpleNamespace(dependencies=None)
        scope = _make_scope(tools=[tool])

        keys = _collect_private_data_keys(scope)

        assert keys == set()

    def test_ignores_non_data_dependency_objects(self) -> None:
        non_dep = SimpleNamespace(data_key="ignored")  # not a DataDependency instance
        tool = SimpleNamespace(dependencies=[non_dep])
        scope = _make_scope(tools=[tool])

        keys = _collect_private_data_keys(scope)

        assert keys == set()
