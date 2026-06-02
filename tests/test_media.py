# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import io
import pytest
from PIL import Image
from profed.media import scale_image


def _jpeg(width: int, height: int) -> bytes:
    img = Image.new("RGB", (width, height), color="red")
    buf = io.BytesIO()

    img.save(buf, format="JPEG")

    return buf.getvalue()


@pytest.mark.asyncio
async def test_scale_image_returns_task(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    task = scale_image(stored.file_id, "large", width=200, height=200)

    assert isinstance(task, asyncio.Task)
    await task


@pytest.mark.asyncio
async def test_scale_image_stores_variant(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    await scale_image(stored.file_id, "small", width=80, height=80)

    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_small"]
    assert content_type == "image/jpeg"
    assert Image.open(io.BytesIO(variant_data)).size == (80, 80)


@pytest.mark.asyncio
async def test_scale_image_publishes_variants_added(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    await scale_image(stored.file_id, "large", width=200, height=200)

    published = fake_bus.topic("media").published
    assert len(published) == 1
    event = published[0]
    assert event["event_type"] == "variants_added"
    assert event["object_id"]== stored.file_id
    assert event["payload"] == {"large": {"url": f"https://fake.example.com/{stored.file_id}_large",
                                          "width": 200,
                                          "height": 200,
                                          "content_type": "image/jpeg"}}

