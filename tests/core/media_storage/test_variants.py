# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
import subprocess

import pytest
from PIL import Image
from unittest.mock import patch


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


def _jpegtran(seen: list, output: bytes, returncode: int = 0):
    def run(command, **kwargs):
        seen.append(kwargs["input"])

        return subprocess.CompletedProcess(command, returncode, output, b"jpegtran said no")

    return patch.object(subprocess, "run", run)


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
async def test_scale_image_transcodes_when_pillow_cannot_decode(fake_bus, fake_media_storage):
    broken = _broken_jpeg()
    seen = []
    stored = await fake_media_storage.store(broken, "image/jpeg")

    with _jpegtran(seen, _jpeg(600, 600)):
        await variants.scale_image(stored.file_id, "x", width=80, height=80)

    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_x"]
    assert seen == [broken]
    assert content_type == "image/jpeg"
    assert Image.open(io.BytesIO(variant_data)).size == (80, 80)


@pytest.mark.asyncio
async def test_scale_image_propagates_when_transcode_also_fails(fake_bus, fake_media_storage):
    seen = []
    stored = await fake_media_storage.store(_broken_jpeg(), "image/jpeg")

    with _jpegtran(seen, b"still-bad"), pytest.raises(OSError):
        await variants.scale_image(stored.file_id, "x", width=80, height=80)

    assert len(seen) == 1
    assert f"{stored.file_id}_x" not in fake_media_storage._files


@pytest.mark.asyncio
async def test_scale_image_reports_what_jpegtran_said(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_broken_jpeg(), "image/jpeg")

    with _jpegtran([], b"", returncode=1), pytest.raises(OSError, match="jpegtran said no"):
        await variants.scale_image(stored.file_id, "x", width=80, height=80)

@pytest.mark.asyncio
async def test_box_image_letterboxes_a_portrait_into_a_square(fake_bus, fake_media_storage):
    stored = await fake_media_storage.store(_jpeg(300, 600), "image/jpeg")

    assert await variants.box_image(stored.file_id, "icon", edge=100) == (100, 100)

    variant_data, content_type = fake_media_storage._files[f"{stored.file_id}_icon"]
    boxed = Image.open(io.BytesIO(variant_data))

    assert content_type == "image/jpeg"
    assert boxed.size == (100, 100)
    assert max(boxed.getpixel((5, 50))) < 20
    assert boxed.getpixel((50, 50))[0] > 200


@pytest.mark.asyncio
async def test_box_image_transcodes_when_pillow_cannot_decode(fake_bus, fake_media_storage):
    broken = _broken_jpeg()
    seen = []
    stored = await fake_media_storage.store(broken, "image/jpeg")

    with _jpegtran(seen, _jpeg(600, 300)):
        assert await variants.box_image(stored.file_id, "icon", edge=100) == (100, 100)

    assert seen == [broken]
    assert Image.open(io.BytesIO(fake_media_storage._files[f"{stored.file_id}_icon"][0])).size == (100, 100)

