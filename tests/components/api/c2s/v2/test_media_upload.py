# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import pytest
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image
from profed.components.api.c2s.v2.media import router as media_module
from profed.components.api.c2s.shared.auth import current_user
from profed.core.media_storage import StoredFile


CLAIMS = {"preferred_username": "alice", "sub": "alice"}
UPLOADER = "alice@test.example"


def make_jpeg(width: int = 100, height: int = 80) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(128, 64, 32)).save(buf, format="JPEG")
    return buf.getvalue()


class FakePublishContext:
    def __init__(self): self.published = []
    async def __aenter__(self):
        async def publish(msg): self.published.append(msg)
        return publish
    async def __aexit__(self, *_): pass


class FakeTopic:
    def __init__(self): self._ctx = FakePublishContext()
    def publish(self): return self._ctx


class FakeBus:
    def __init__(self): self._media = FakeTopic()
    def topic(self, name): return self._media


class FakeStorage:
    async def store(self, file_id, data, content_type):
        return StoredFile(file_id=file_id,
                          url=f"https://example.com/media/ab/{file_id}",
                          content_type=content_type,
                          size=len(data))


@pytest.fixture
def client():
    media_module.init({})
    app = FastAPI()
    app.include_router(media_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


@pytest.fixture(autouse=True)
def mocks():
    bus     = FakeBus()
    storage = FakeStorage()
    with patch("profed.components.api.c2s.shared.media.upload.message_bus", return_value=bus), \
         patch("profed.components.api.c2s.shared.media.upload.media_storage", return_value=storage), \
         patch("profed.components.api.c2s.shared.media.upload.acct_from_username", return_value=UPLOADER):
        yield bus, storage


def test_upload_jpeg_returns_media_attachment(client):
    response = client.post("/media", files={"file": ("photo.jpg", make_jpeg(), "image/jpeg")})

    assert response.status_code == 200
    data = response.json()
    assert data["type"] == "image"
    assert data["url"].startswith("https")
    assert data["preview_url"] is not None
    assert data["meta"]["original"]["width"] == 100
    assert data["meta"]["original"]["height"] == 80


def test_upload_publishes_event(client, mocks):
    bus, _ = mocks
    client.post("/media", files={"file": ("photo.jpg", make_jpeg(), "image/jpeg")})

    published = bus.topic("media")._ctx.published
    assert len(published) == 1
    assert published[0]["type"] == "uploaded"
    assert published[0]["payload"]["content_type"] == "image/jpeg"
    assert published[0]["payload"]["uploader"] == UPLOADER


def test_unsupported_type_returns_422(client):
    response = client.post("/media", files={"file": ("doc.pdf", b"data", "application/pdf")})

    assert response.status_code == 422


def test_upload_with_description(client):
    response = client.post("/media",
                           files={"file": ("photo.jpg", make_jpeg(), "image/jpeg")},
                           data={"description": "Ein Testbild"})

    assert response.status_code == 200
    assert response.json()["description"] == "Ein Testbild"


def test_thumbnail_is_smaller_than_original(client):
    response = client.post("/media",
                           files={"file": ("large.jpg", make_jpeg(800, 600), "image/jpeg")})

    meta = response.json()["meta"]
    assert meta["small"]["width"]  <= 400
    assert meta["small"]["height"] <= 400

