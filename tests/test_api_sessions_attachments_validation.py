from __future__ import annotations

import base64
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from maivn_studio.api.routes.sessions import helpers as sessions_helpers
from maivn_studio.api.routes.sessions import models as sessions_models
from maivn_studio.api.routes.sessions import writes as sessions_writes
from maivn_studio.config.models import DemoConfig, DemoVariant, StudioConfig


class _DummyRegistry:
    def __init__(self, demo: DemoConfig) -> None:
        self._demo = demo

    def get(self, demo_id: str) -> DemoConfig | None:
        if demo_id == self._demo.id:
            return self._demo
        return None


class _DummyCreateSession:
    session_id = "session-1"


class _DummyCreateManager:
    async def create_session(self, **_: object) -> _DummyCreateSession:
        return _DummyCreateSession()

    async def start_session(self, *_: object, **__: object) -> None:
        raise ValueError("Attachment exceeds maximum supported size")


class _CapturingCreateManager:
    def __init__(self) -> None:
        self.create_kwargs: dict[str, object] | None = None

    async def create_session(self, **kwargs: object) -> _DummyCreateSession:
        self.create_kwargs = kwargs
        return _DummyCreateSession()

    async def start_session(self, *_: object, **__: object) -> None:
        raise ValueError("stop after create")


class _DummyStatus:
    value = "ready"


class _DummySendSession:
    can_send_message = True
    status = _DummyStatus()


class _DummySendManager:
    def __init__(self, session: _DummySendSession) -> None:
        self._session = session

    def get(self, _session_id: str) -> _DummySendSession:
        return self._session

    async def send_message(self, *_: object, **__: object) -> None:
        raise ValueError("Attachment exceeds maximum supported size")


def _attachment_b64(content: bytes = b"hello") -> str:
    return base64.b64encode(content).decode("ascii")


def test_message_attachment_payload_requires_content_base64() -> None:
    with pytest.raises(ValidationError):
        sessions_models.MessageAttachmentPayload.model_validate({"name": "example.txt"})


def test_message_attachment_payload_rejects_invalid_base64() -> None:
    with pytest.raises(ValidationError):
        sessions_models.MessageAttachmentPayload.model_validate(
            {"content_base64": "not-valid-base64*"}
        )


def test_message_attachment_payload_allows_source_url_metadata() -> None:
    payload = sessions_models.MessageAttachmentPayload(
        name="example.txt",
        source_url="https://example.com/example.txt",
        content_base64=_attachment_b64(),
    )

    assert payload.source_url == "https://example.com/example.txt"
    assert payload.content_base64 == _attachment_b64()


def test_create_session_request_rejects_attachment_without_content_base64() -> None:
    with pytest.raises(ValidationError):
        sessions_models.CreateSessionRequest.model_validate(
            {
                "demo_id": "demo-1",
                "message": "hello",
                "attachments": [
                    {
                        "name": "example.txt",
                        "source_url": "https://example.com/example.txt",
                    }
                ],
            }
        )


@pytest.mark.asyncio
async def test_create_session_maps_attachment_value_error_to_http_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = DemoConfig(
        id="demo-1",
        name="Demo One",
        module="demos.demo_one",
    )

    monkeypatch.setattr(sessions_writes, "get_registry", lambda: _DummyRegistry(demo))
    monkeypatch.setattr(sessions_writes, "get_session_manager", lambda: _DummyCreateManager())
    monkeypatch.setattr(sessions_writes, "create_event_bridge", lambda _session_id: None)

    request = sessions_models.CreateSessionRequest(
        demo_id="demo-1",
        message="hello",
        attachments=[
            sessions_models.MessageAttachmentPayload(
                name="example.txt", content_base64=_attachment_b64()
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        await sessions_writes.create_session(request)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Attachment exceeds maximum supported size"


@pytest.mark.asyncio
async def test_send_message_maps_attachment_value_error_to_http_422(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _DummySendSession()
    monkeypatch.setattr(sessions_writes, "get_session_manager", lambda: _DummySendManager(session))

    request = sessions_models.SendMessageRequest(
        message="hello",
        attachments=[
            sessions_models.MessageAttachmentPayload(
                name="example.txt", content_base64=_attachment_b64()
            )
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        await sessions_writes.send_message("session-1", request)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Attachment exceeds maximum supported size"


@pytest.mark.asyncio
async def test_create_session_refreshes_registry_private_data_from_disk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stale_demo = DemoConfig(
        id="demo-1",
        name="Demo One",
        module="demos.demo_one",
        private_data={"manufacturer": "Cote Robotics"},
    )
    refreshed_demo = DemoConfig(
        id="demo-1",
        name="Demo One",
        module="demos.demo_one",
        private_data={
            "manufacturer": "Cote Robotics",
            "serial_number": "SN-RWX1-2049A",
        },
    )
    registry = _DummyRegistry(stale_demo)
    manager = _CapturingCreateManager()

    monkeypatch.setattr(sessions_writes, "get_registry", lambda: registry)
    monkeypatch.setattr(sessions_writes, "get_session_manager", lambda: manager)
    monkeypatch.setattr(sessions_writes, "create_event_bridge", lambda _session_id: None)
    monkeypatch.setattr(
        sessions_helpers,
        "get_config_path",
        lambda: Path(
            "c:/Users/chad6/Repo/MaivnProjects/maivn-apps/apps/maivn-demos/maivn_studio.json"
        ),
    )
    monkeypatch.setattr(
        sessions_helpers,
        "reload_config",
        lambda: StudioConfig(demos=[refreshed_demo]),
    )
    monkeypatch.setattr(sessions_helpers, "set_config", lambda _config, _config_path: None)

    def _init_registry(config: StudioConfig, _base_path: Path) -> None:
        registry._demo = config.demos[0]

    monkeypatch.setattr(sessions_helpers, "init_registry", _init_registry)

    request = sessions_models.CreateSessionRequest(
        demo_id="demo-1",
        message="hello",
    )

    with pytest.raises(HTTPException) as exc_info:
        await sessions_writes.create_session(request)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "stop after create"
    assert manager.create_kwargs is not None
    assert manager.create_kwargs["private_data"] == {
        "manufacturer": "Cote Robotics",
        "serial_number": "SN-RWX1-2049A",
    }


@pytest.mark.asyncio
async def test_create_session_uses_default_variant_when_request_omits_variant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = DemoConfig(
        id="demo-1",
        name="Demo One",
        module="demos.demo_one",
        variants={"newsletter": DemoVariant(args=["--newsletter"], description="Newsletter")},
        default_variant="newsletter",
    )
    manager = _CapturingCreateManager()

    monkeypatch.setattr(sessions_writes, "get_registry", lambda: _DummyRegistry(demo))
    monkeypatch.setattr(sessions_writes, "get_session_manager", lambda: manager)
    monkeypatch.setattr(sessions_writes, "create_event_bridge", lambda _session_id: None)

    request = sessions_models.CreateSessionRequest(
        demo_id="demo-1",
        message="hello",
    )

    with pytest.raises(HTTPException) as exc_info:
        await sessions_writes.create_session(request)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "stop after create"
    assert manager.create_kwargs is not None
    assert manager.create_kwargs["variant"] == "newsletter"


@pytest.mark.asyncio
async def test_create_session_merges_variant_private_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    demo = DemoConfig(
        id="demo-1",
        name="Demo One",
        module="demos.demo_one",
        private_data={"shared_key": "demo-default", "shared_override": "demo-value"},
        variants={
            "with-private-data": DemoVariant(
                args=[],
                description="Private data variant",
                private_data={
                    "shared_override": "variant-value",
                    "secret_token": "variant-token",
                },
            )
        },
    )
    manager = _CapturingCreateManager()

    monkeypatch.setattr(sessions_writes, "get_registry", lambda: _DummyRegistry(demo))
    monkeypatch.setattr(sessions_writes, "get_session_manager", lambda: manager)
    monkeypatch.setattr(sessions_writes, "create_event_bridge", lambda _session_id: None)

    request = sessions_models.CreateSessionRequest(
        demo_id="demo-1",
        message="hello",
        variant="with-private-data",
        private_data={"shared_override": "request-value", "request_only": "user-value"},
    )

    with pytest.raises(HTTPException) as exc_info:
        await sessions_writes.create_session(request)

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "stop after create"
    assert manager.create_kwargs is not None
    assert manager.create_kwargs["variant"] == "with-private-data"
    assert manager.create_kwargs["private_data"] == {
        "shared_key": "demo-default",
        "shared_override": "request-value",
        "secret_token": "variant-token",
        "request_only": "user-value",
    }
