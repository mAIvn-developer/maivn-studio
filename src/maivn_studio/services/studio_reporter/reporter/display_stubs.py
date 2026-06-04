# pyright: strict
"""Display + progress stubs.

Studio is headless; the terminal display surface of :class:`BaseReporter` is
not relevant here. These methods are required by the protocol but intentionally
no-op so the SDK can call them without crashing or producing console output.
"""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from maivn_shared.utils.token_models import TokenUsage

# MARK: Display Stubs


class DisplayStubsMixin:
    """No-op terminal display methods for the headless Studio reporter.

    These methods override :class:`BaseReporter` callbacks only once the mixin
    is composed into :class:`StudioReporter`; the mixin itself does not inherit
    ``BaseReporter``, so ``@override`` is intentionally omitted here.
    """

    def print_header(self, title: str, subtitle: str = "") -> None:
        _ = (title, subtitle)
        return

    def print_section(self, title: str, style: str = "bold cyan") -> None:
        _ = (title, style)
        return

    def print_event(
        self,
        event_type: str,
        message: str,
        details: dict[str, object] | None = None,
    ) -> None:
        _ = (event_type, message, details)
        return

    def print_summary(self, token_usage: TokenUsage | None = None) -> None:
        _ = token_usage
        return

    def print_final_result(self, result: object) -> None:
        _ = result
        return

    def print_error_summary(self, error: str) -> None:
        _ = error
        return

    # MARK: - Progress

    @contextmanager
    def live_progress(self, description: str = "Processing...") -> Generator[object, None, None]:
        _ = description
        yield None

    def update_progress(self, task_id: object, description: str | None = None) -> None:
        _ = (task_id, description)
        return

    # MARK: - Input scaffolding

    @contextmanager
    def prepare_for_user_input(self) -> Generator[None, None, None]:
        yield


__all__ = ["DisplayStubsMixin"]
