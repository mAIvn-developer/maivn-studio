"""User-input routing: SDK ``get_input`` → SSE interrupt → frontend → response."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("maivn_studio.services.studio_reporter.reporter")


# MARK: Input Mixin


class InputMixin:
    """Implements :meth:`BaseReporter.get_input` by emitting an interrupt event.

    Studio routes user input through the bridge instead of stdin. The flow:

    1. SDK calls ``get_input`` from a tool dependency.
    2. We register an interrupt id, emit an ``interrupt_required`` event, and
       block on the event's resolution future (with a 7-day soft cap).
    3. The frontend POSTs to ``/sessions/{id}/interrupt`` with the user's
       answer; the route resolves the registered future.
    4. We collect the value and return it to the SDK, which proceeds.
    """

    # Attributes provided by :class:`StudioReporter` (declared here so pyright
    # can typecheck the mixin in isolation).
    _bridge: Any
    _turn_id: str
    _interrupt_counter: int
    _current_tool_name: str | None
    _submit: Any

    @property
    def session_id(self) -> str:  # pragma: no cover - provided by StudioReporter
        raise NotImplementedError

    def get_input(
        self,
        prompt: str,
        *,
        input_type: str = "text",
        choices: list[str] | None = None,
        data_key: str | None = None,
        arg_name: str | None = None,
    ) -> str:
        """Collect input via UI instead of terminal.

        Emits an interrupt_required SSE event and waits for the response
        to be provided via the resolve_interrupt API.

        Args:
            prompt: The prompt to display to the user.
            input_type: Type of input (text, choice, boolean, number, email, password).
            choices: Available choices for choice/literal input types.
            data_key: Optional data key for interrupt storage.
            arg_name: Optional argument name in the tool signature.

        Returns:
            The user's input string.
        """
        # Look the interrupt helpers up via the reporter package each call so
        # ``mock.patch("maivn_studio.services.studio_reporter.reporter.<name>", ...)``
        # — used heavily by the test suite — continues to intercept the call
        # after the reporter module was split into a subpackage.
        from . import cleanup_interrupt, get_interrupt_response, register_interrupt

        # Generate unique interrupt ID (includes turn_id to avoid collisions across turns)
        self._interrupt_counter += 1
        interrupt_id = f"{self.session_id}-interrupt-{self._turn_id}-{self._interrupt_counter}"

        logger.info(
            f'[STUDIO_REPORTER] get_input called: prompt="{prompt[:50]}...", '
            f"interrupt_id={interrupt_id}, input_type={input_type}, choices={choices}"
        )

        resolved_data_key = data_key or arg_name or interrupt_id
        interrupt_aliases = [f"{self.session_id}:{resolved_data_key}"]
        if arg_name and arg_name != resolved_data_key:
            interrupt_aliases.append(f"{self.session_id}:{arg_name}")

        # Register the interrupt and get the event to wait on
        wait_event = register_interrupt(interrupt_id, aliases=interrupt_aliases)

        # Always emit the interrupt event from the reporter — the reporter
        # owns the interrupt_id that the resolve API uses.  The contract
        # stream normalizer skips interrupt_required events to avoid
        # duplicate cards with mismatched IDs.
        self._submit(
            self._bridge.emit_interrupt_required(
                interrupt_id=interrupt_id,
                data_key=resolved_data_key,
                prompt=prompt.strip(),
                arg_name=arg_name,
                tool_name=self._current_tool_name,
                input_type=input_type,
                choices=choices,
            )
        )

        logger.info(f"[STUDIO_REPORTER] Waiting for interrupt response: {interrupt_id}")

        # Wait for the response (blocks until resolve_interrupt is called).
        # Interrupts are designed for long waits (up to 7 days) — the server
        # checkpoints them so they don't hold up resources.
        if not wait_event.wait(timeout=604800):
            logger.warning(f"[STUDIO_REPORTER] Interrupt {interrupt_id} timed out")
            cleanup_interrupt(interrupt_id)
            return ""

        # Get the response
        response = get_interrupt_response(interrupt_id)
        cleanup_interrupt(interrupt_id)

        logger.info(
            f"[STUDIO_REPORTER] Received interrupt response: {interrupt_id} -> "
            f'"{response[:50] if response else "(empty)"}"'
        )

        return response or ""


__all__ = ["InputMixin"]
