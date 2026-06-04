"""Tests for the interrupt registry service."""

# pyright: strict
from __future__ import annotations

import threading

import maivn_studio.services.studio_reporter.interrupts as interrupts_module
from maivn_studio.services.studio_reporter.interrupts import (
    cleanup_interrupt,
    get_interrupt_response,
    register_interrupt,
    resolve_interrupt,
)

# MARK: Fixtures / Helpers


def _cleanup_registry() -> None:
    """Reset global registry state between tests."""
    with interrupts_module.interrupt_lock:
        interrupts_module.pending_interrupts.clear()


# MARK: register_interrupt


class TestRegisterInterrupt:
    def setup_method(self) -> None:
        _cleanup_registry()

    def test_returns_threading_event(self) -> None:
        event = register_interrupt("int-1")
        assert isinstance(event, threading.Event)
        assert not event.is_set()

    def test_registers_entry_in_registry(self) -> None:
        register_interrupt("int-2")
        assert "int-2" in interrupts_module.pending_interrupts

    def test_registers_session_scoped_aliases(self) -> None:
        register_interrupt("int-3", aliases=["session-1:user_name"])
        assert interrupts_module.interrupt_aliases["session-1:user_name"] == "int-3"


# MARK: resolve_interrupt


class TestResolveInterrupt:
    def setup_method(self) -> None:
        _cleanup_registry()

    def test_sets_event_and_stores_response(self) -> None:
        event = register_interrupt("int-1")
        result = resolve_interrupt("int-1", "user_response")

        assert result is True
        assert event.is_set()

    def test_returns_false_for_nonexistent_id(self) -> None:
        result = resolve_interrupt("nonexistent", "value")
        assert result is False

    def test_resolves_via_alias(self) -> None:
        event = register_interrupt("int-2", aliases=["session-1:user_name"])
        result = resolve_interrupt("session-1:user_name", "user_response")

        assert result is True
        assert event.is_set()


# MARK: get_interrupt_response


class TestGetInterruptResponse:
    def setup_method(self) -> None:
        _cleanup_registry()

    def test_returns_stored_response(self) -> None:
        register_interrupt("int-1")
        resolve_interrupt("int-1", "answer")
        response = get_interrupt_response("int-1")
        assert response == "answer"

    def test_returns_none_for_nonexistent_id(self) -> None:
        assert get_interrupt_response("missing") is None

    def test_returns_none_before_resolve(self) -> None:
        register_interrupt("int-1")
        assert get_interrupt_response("int-1") is None


# MARK: cleanup_interrupt


class TestCleanupInterrupt:
    def setup_method(self) -> None:
        _cleanup_registry()

    def test_removes_from_registry(self) -> None:
        register_interrupt("int-1")
        cleanup_interrupt("int-1")
        assert "int-1" not in interrupts_module.pending_interrupts

    def test_noop_for_nonexistent_id(self) -> None:
        # Should not raise
        cleanup_interrupt("nonexistent")

    def test_removes_aliases_from_registry(self) -> None:
        register_interrupt("int-2", aliases=["session-1:user_name"])
        cleanup_interrupt("int-2")
        assert resolve_interrupt("session-1:user_name", "value") is False


# MARK: Full Flow


class TestFullFlow:
    def setup_method(self) -> None:
        _cleanup_registry()

    def test_register_resolve_get_cleanup(self) -> None:
        # 1. Register
        event = register_interrupt("flow-1")
        assert not event.is_set()

        # 2. Resolve
        assert resolve_interrupt("flow-1", "my_answer") is True
        assert event.is_set()

        # 3. Get response
        assert get_interrupt_response("flow-1") == "my_answer"

        # 4. Cleanup
        cleanup_interrupt("flow-1")
        assert get_interrupt_response("flow-1") is None

    def test_concurrent_resolve_via_thread(self) -> None:
        event = register_interrupt("thread-1")

        def resolver() -> None:
            resolve_interrupt("thread-1", "threaded_answer")

        t = threading.Thread(target=resolver)
        t.start()
        event.wait(timeout=5.0)
        t.join()

        assert event.is_set()
        assert get_interrupt_response("thread-1") == "threaded_answer"
