# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io

import pytest
from PIL import Image
from unittest.mock import Mock, patch
from profed.components.api.c2s.shared.media.upload import process_upload


def _png(width=800, height=600) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 90, 120)).save(buffer, format="PNG")

    return buffer.getvalue()


def _file(data=None, content_type="image/png"):
    async def read():
        return _png() if data is None else data

    upload = Mock()
    upload.content_type = content_type
    upload.read = read

    return upload


@pytest.fixture
def uploading(fake_bus, fake_media_storage):
    with patch("profed.components.api.c2s.shared.media.upload.scale_image", Mock()):
        yield fake_bus


@pytest.mark.asyncio
async def test_the_alt_text_travels_with_the_uploaded_object(uploading):
    await process_upload("alice", _file(), "Ein Diagramm")

    published = uploading.topic("media").published
    assert published[0]["event_type"] == "uploaded"
    assert published[0]["payload"]["description"] == "Ein Diagramm"


@pytest.mark.asyncio
async def test_the_alt_text_comes_back_on_the_attachment(uploading):
    attachment = await process_upload("alice", _file(), "Ein Diagramm")

    assert attachment.description == "Ein Diagramm"


@pytest.mark.asyncio
async def test_markup_in_the_alt_text_is_stripped_before_it_is_stored(uploading):
    await process_upload("alice", _file(), "<b>fett</b><script>steal()</script>")

    assert "<" not in uploading.topic("media").published[0]["payload"]["description"]


@pytest.mark.asyncio
async def test_an_upload_without_an_alt_text_carries_none(uploading):
    await process_upload("alice", _file(), None)

    assert "description" not in uploading.topic("media").published[0]["payload"]


@pytest.mark.asyncio
async def test_the_dimensions_travel_with_the_uploaded_object(uploading):
    await process_upload("alice", _file(_png(1920, 1080)), None)

    assert uploading.topic("media").published[0]["payload"]["metadata"] == {"kind": "image",
                                                                            "width": 1920,
                                                                            "height": 1080}

