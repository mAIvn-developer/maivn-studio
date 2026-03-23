from __future__ import annotations

import base64

import pytest
from langchain_core.messages import HumanMessage as LangChainHumanMessage
from langchain_core.messages import SystemMessage

from maivn_studio.services.session_manager.manager import SessionManager
from maivn_studio.services.session_manager.messages import RedactedMessage


def _build_attachment() -> dict[str, str]:
    return {
        "name": "notes.txt",
        "mime_type": "text/plain",
        "content_base64": base64.b64encode(b"hello").decode("ascii"),
    }


def test_create_message_supports_human_attachments() -> None:
    manager = SessionManager()

    message = manager._create_message(
        "Please index this attachment.",
        "human",
        attachments=[_build_attachment()],
    )

    assert isinstance(message, LangChainHumanMessage)
    attachments = message.additional_kwargs.get("attachments")
    assert isinstance(attachments, list)
    assert attachments[0]["name"] == "notes.txt"
    assert attachments[0]["mime_type"] == "text/plain"


@pytest.mark.skipif(RedactedMessage is None, reason="maivn RedactedMessage unavailable")
def test_create_message_supports_redacted_attachments() -> None:
    manager = SessionManager()

    message = manager._create_message(
        "Top secret",
        "redacted",
        attachments=[_build_attachment()],
    )

    attachments = message.additional_kwargs.get("attachments")
    assert isinstance(attachments, list)
    assert attachments[0]["name"] == "notes.txt"


def test_create_message_ignores_attachments_for_system_messages() -> None:
    manager = SessionManager()

    message = manager._create_message(
        "System instruction",
        "system",
        attachments=[_build_attachment()],
    )

    assert isinstance(message, SystemMessage)
    assert message.additional_kwargs.get("attachments") is None
