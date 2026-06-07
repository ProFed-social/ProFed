# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io

import pytest
from PIL import Image


from profed.core.media_storage import variants


def _jpeg(width: int, height: int, mode: str = "RGB", color = "red") -> bytes:
    img = Image.new(mode, (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _broken_jpeg() -> bytes:
    noise = bytes((i * 37 + 11) % 256 for i in range(96 * 96 * 3))
    buf = io.BytesIO()
    Image.frombytes("RGB", (96, 96), noise).resize((600, 600)).save(buf, format="JPEG", quality=90)
    data = bytearray(buf.getvalue())
    sos = data.find(b"\xff\xda")
    for index in range(sos + 200, sos + 1700, 7):
        data[index] ^= 0xFF
    return bytes(data)


def _png(width: int, height: int, mode: str = "RGBA") -> bytes:
    img = Image.new(mode, (width, height), color=(255, 0, 0, 128))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _animated_gif() -> bytes:
    frames = [Image.new("RGB", (100, 100), color=c) for c in ("red", "green", "blue")]
    buf    = io.BytesIO()
    frames[0].save(buf,
                   format=        "GIF",
                   save_all=      True,
                   append_images= frames[1:],
                   duration=      100,
                   loop=          0)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_scale_image_with_both_dimensions(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    await variants.scale_image(stored.file_id, "large", width=200, height=200)

    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_large"]
    assert content_type == "image/jpeg"
    assert Image.open(io.BytesIO(variant_data)).size == (200, 200)


@pytest.mark.asyncio
async def test_scale_image_only_width_preserves_aspect(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    await variants.scale_image(stored.file_id, "wide", width=400)

    variant_data, _ = fake_media_storage._files[f"{stored.file_id}_wide"]
    assert Image.open(io.BytesIO(variant_data)).size == (400, 300)


@pytest.mark.asyncio
async def test_scale_image_only_height_preserves_aspect(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(800, 600), "image/jpeg")

    await variants.scale_image(stored.file_id, "tall", height=300)

    variant_data, _ = fake_media_storage._files[f"{stored.file_id}_tall"]
    assert Image.open(io.BytesIO(variant_data)).size == (400, 300)


@pytest.mark.asyncio
async def test_scale_image_no_dimensions_raises(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(100, 100), "image/jpeg")

    with pytest.raises(ValueError, match="at least one of width, height"):
        await variants.scale_image(stored.file_id, "fail")


@pytest.mark.asyncio
async def test_scale_image_png_with_alpha_preserves_rgba(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_png(400, 400, mode="RGBA"), "image/png")

    await variants.scale_image(stored.file_id, "small", width=80, height=80)

    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_small"]
    assert content_type == "image/png"

    img = Image.open(io.BytesIO(variant_data))
    assert img.format == "PNG"
    assert img.mode   == "RGBA"


@pytest.mark.asyncio
async def test_scale_image_jpeg_stays_jpeg(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(400, 400), "image/jpeg")

    await variants.scale_image(stored.file_id, "small", width=80, height=80)

    _, content_type = fake_media_storage._files[f"{stored.file_id}_small"]
    assert content_type == "image/jpeg"
    assert Image.open(io.BytesIO(fake_media_storage._files[f"{stored.file_id}_small"][0])).format == "JPEG"


@pytest.mark.asyncio
async def test_scale_image_cmyk_jpeg_converts_to_rgb(fake_bus, fake_media_storage):
    img = Image.new("CMYK", (800, 600), color=(0, 100, 100, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    stored = await fake_media_storage.store(buf.getvalue(), "image/jpeg")

    await variants.scale_image(stored.file_id, "large", width=200, height=200)

    variant_data, _ = fake_media_storage._files[f"{stored.file_id}_large"]
    assert Image.open(io.BytesIO(variant_data)).mode == "RGB"


@pytest.mark.asyncio
async def test_scale_image_animated_gif_raises(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_animated_gif(), "image/gif")

    with pytest.raises(ValueError, match="cannot scale animated"):
        await variants.scale_image(stored.file_id, "large", width=50, height=50)


@pytest.mark.asyncio
async def test_scale_image_raises_on_unrecoverable_jpeg(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_broken_jpeg(), "image/jpeg")

    with pytest.raises(OSError):
        await variants.scale_image(stored.file_id, "small", width=80, height=80)


@pytest.mark.asyncio
async def test_scale_image_transcodes_when_pillow_cannot_decode(monkeypatch, fake_bus, fake_media_storage):
    seen = []
    def fake_scale(image_bytes, width, height):
        seen.append(image_bytes)
        if image_bytes == b"undecodable":
            raise OSError("broken data stream")
        return (b"scaled-bytes", width, height, "image/jpeg")
    monkeypatch.setattr(variants, "_scale_pillow", fake_scale)
    monkeypatch.setattr(variants, "_transcode_baseline", lambda data: b"transcoded")
    stored = await fake_media_storage.store(b"undecodable", "image/jpeg")

    await variants.scale_image(stored.file_id, "x", width=80, height=80)

    assert seen == [b"undecodable", b"transcoded"]
    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_x"]
    assert variant_data == b"scaled-bytes"
    assert content_type == "image/jpeg"
@pytest.mark.asyncio
async def test_scale_image_propagates_when_transcode_also_fails(monkeypatch,
                                                                fake_bus,
                                                                fake_media_storage):
    def always_fail(image_bytes, width, height):
        raise OSError("still broken")
    monkeypatch.setattr(variants, "_scale_pillow", always_fail)
    monkeypatch.setattr(variants, "_transcode_baseline", lambda data: b"still-bad")

    stored = await fake_media_storage.store(b"undecodable", "image/jpeg")

    with pytest.raises(OSError):
        await variants.scale_image(stored.file_id, "x", width=80, height=80)

