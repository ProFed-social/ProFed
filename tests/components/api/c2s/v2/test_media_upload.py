# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import pytest
from uuid import uuid4

from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from profed.components.api.c2s.v2.media import router as media_module
from profed.components.api.c2s.shared.auth import current_user
from profed.core.media_storage import StoredFile

from _fakes import FakeMessageBus


CLAIMS = {"preferred_username": "alice", "sub": "alice"}
UPLOADER = "alice@test.example"


def make_jpeg(width: int = 100, height: int = 80) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (width, height), color=(128, 64, 32)).save(buf, format="JPEG")
    return buf.getvalue()


class FakeStorage:
    async def store(self, data, content_type):
        file_id = str(uuid4()).replace("-", "")
        return StoredFile(file_id=file_id,
                          url=self.url_for(file_id),
                          content_type=content_type,
                          size=len(data))

    async def add_variant(self, file_id, variant, data, content_type):
        return StoredFile(file_id=file_id,
                          url=self.url_for(file_id, variant),
                          content_type=content_type,
                          size=len(data))

    def url_for(self, file_id, variant=None):
        suffix = f"_{variant}" if variant else ""
        return f"https://example.com/media/ab/{file_id}{suffix}"


@pytest.fixture
def client():
    media_module.init({})
    app = FastAPI()
    app.include_router(media_module.router)
    app.dependency_overrides[current_user] = lambda: CLAIMS
    return TestClient(app)


@pytest.fixture(autouse=True)
def mocks():
    bus     = FakeMessageBus()
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

    published = bus.topic("media").published
    assert len(published) == 1
    assert published[0]["event_type"] == "uploaded"
    assert published[0]["object_id"]
    payload = published[0]["payload"]
    assert payload["content_type"] == "image/jpeg"
    assert payload["uploader"] == UPLOADER
    assert payload["metadata"] == {"kind": "image", "width": 100, "height": 80}
    assert "preview_url" not in payload
    assert "preview_width" not in payload


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

