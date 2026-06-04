# pyright: strict
from __future__ import annotations

import base64
from typing import Any, cast

import pytest
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.messages import HumanMessage as LangChainHumanMessage

from maivn_studio.services.session_manager.manager import SessionManager
from maivn_studio.services.session_manager.messages import RedactedMessage


def _build_attachment() -> dict[str, str]:
    return {
        "name": "notes.txt",
        "mime_type": "text/plain",
        "content_base64": base64.b64encode(b"hello").decode("ascii"),
    }


def _get_attachments(message: BaseMessage) -> Any:
    """Read the ``attachments`` entry from a LangChain message.

    ``BaseMessage.additional_kwargs`` is typed as ``dict[Any, Any]`` by
    langchain_core, so narrow it to a studio-known shape at the boundary.
    """
    additional_kwargs = cast(dict[str, Any], message.additional_kwargs)
    return additional_kwargs.get("attachments")


def test_create_message_supports_human_attachments() -> None:
    manager = SessionManager()

    message = manager.create_message(
        "Please index this attachment.",
        "human",
        attachments=[_build_attachment()],
    )

    assert isinstance(message, LangChainHumanMessage)
    attachments = _get_attachments(message)
    assert isinstance(attachments, list)
    attachments_list = cast(list[dict[str, str]], attachments)
    assert attachments_list[0]["name"] == "notes.txt"
    assert attachments_list[0]["mime_type"] == "text/plain"


@pytest.mark.skipif(RedactedMessage is None, reason="maivn RedactedMessage unavailable")
def test_create_message_supports_redacted_attachments() -> None:
    manager = SessionManager()

    message = manager.create_message(
        "Top secret",
        "redacted",
        attachments=[_build_attachment()],
    )

    attachments = _get_attachments(message)
    assert isinstance(attachments, list)
    attachments_list = cast(list[dict[str, str]], attachments)
    assert attachments_list[0]["name"] == "notes.txt"


def test_create_message_ignores_attachments_for_system_messages() -> None:
    manager = SessionManager()

    message = manager.create_message(
        "System instruction",
        "system",
        attachments=[_build_attachment()],
    )

    assert isinstance(message, SystemMessage)
    assert _get_attachments(message) is None
