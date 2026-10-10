# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io

import pytest
from PIL import Image
from fastapi import HTTPException
from unittest.mock import AsyncMock, Mock, patch
from profed.models import AudioMeta, DocumentMeta, VideoMeta
from profed.components.api.c2s.shared.media import upload
from profed.components.api.c2s.shared.media.upload import process_upload


VIDEO_META = VideoMeta(width=1920, height=1080, duration=12.5)
AUDIO_META = AudioMeta(duration=2.5)
DOCUMENT_META = DocumentMeta(pages=12, width=794, height=1123)


def _measured(metadata, poster=None):
    return patch.object(upload, "measured", AsyncMock(return_value=(metadata, poster)))


def _png(width=800, height=600) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (40, 90, 120)).save(buffer, format="PNG")

    return buffer.getvalue()


def _file(data=None, content_type="image/png", filename="picture.png"):
    async def read():
        return _png() if data is None else data

    upload = Mock()
    upload.content_type = content_type
    upload.filename = filename
    upload.read = read

    return upload


@pytest.fixture
def uploading(api_config, fake_bus, fake_media_storage):
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


@pytest.mark.asyncio
async def test_a_type_we_cannot_handle_is_refused(uploading):
    with pytest.raises(HTTPException) as refused:
        await process_upload("alice", _file(b"data", "application/zip", "bundle.zip"), None)

    assert refused.value.status_code == 422
    assert refused.value.detail == "unsupported_media_type"


@pytest.mark.asyncio
async def test_a_file_over_the_limit_of_its_kind_is_refused(uploading, api_config):
    too_large = b"x" * (api_config["api"]["image_size_limit"] + 1)

    with pytest.raises(HTTPException) as refused:
        await process_upload("alice", _file(too_large), None)

    assert refused.value.detail == "file_too_large"


@pytest.mark.asyncio
async def test_each_kind_is_measured_against_its_own_limit(uploading, api_config):
    beyond_images = b"x" * (api_config["api"]["image_size_limit"] + 1)

    with _measured(VIDEO_META):
        attachment = await process_upload("alice", _file(beyond_images, "video/mp4", "clip.mp4"), None)

    assert attachment.type == "video"


@pytest.mark.asyncio
async def test_a_video_is_announced_as_a_video_with_its_dimensions(uploading):
    with _measured(VIDEO_META, b"poster"):
        attachment = await process_upload("alice", _file(b"clip", "video/mp4", "clip.mp4"), None)

    assert attachment.type == "video"
    assert attachment.mime_type == "video/mp4"
    assert (attachment.meta.original.width, attachment.meta.original.height) == (1920, 1080)


@pytest.mark.asyncio
async def test_a_video_carries_its_duration_on_the_attachment(uploading):
    with _measured(VIDEO_META, b"poster"):
        attachment = await process_upload("alice", _file(b"clip", "video/mp4", "clip.mp4"), None)

    assert attachment.meta.original.duration == 12.5


@pytest.mark.asyncio
async def test_the_poster_of_a_video_becomes_its_preview(uploading, fake_media_storage):
    with _measured(VIDEO_META, b"poster"):
        attachment = await process_upload("alice", _file(b"clip", "video/mp4", "clip.mp4"), None)

    assert attachment.preview_url.endswith("_small")
    assert await fake_media_storage.retrieve(f"{attachment.id}_small") == b"poster"


@pytest.mark.asyncio
async def test_a_video_metadata_travels_with_the_uploaded_object(uploading):
    with _measured(VIDEO_META):
        await process_upload("alice", _file(b"clip", "video/mp4", "clip.mp4"), None)

    assert uploading.topic("media").published[0]["payload"]["metadata"] == {"kind": "video",
                                                                            "width": 1920,
                                                                            "height": 1080,
                                                                            "duration": 12.5}


@pytest.mark.asyncio
async def test_a_video_we_cannot_measure_is_still_accepted(uploading):
    with _measured(None):
        attachment = await process_upload("alice", _file(b"clip", "video/mp4", "clip.mp4"), None)

    assert attachment.type == "video"
    assert attachment.meta is None
    assert "metadata" not in uploading.topic("media").published[0]["payload"]


@pytest.mark.asyncio
async def test_an_audio_file_is_announced_as_audio_with_its_duration(uploading):
    with _measured(AUDIO_META):
        attachment = await process_upload("alice", _file(b"tone", "audio/mpeg", "tone.mp3"), None)

    assert attachment.type == "audio"
    assert attachment.meta.original.duration == 2.5


@pytest.mark.asyncio
async def test_an_audio_file_gets_no_preview_image(uploading):
    with _measured(AUDIO_META):
        attachment = await process_upload("alice", _file(b"tone", "audio/mpeg", "tone.mp3"), None)

    assert attachment.preview_url is None


@pytest.mark.asyncio
async def test_a_pdf_is_announced_as_unknown_to_mastodon_but_names_its_type(uploading):
    with _measured(DOCUMENT_META):
        attachment = await process_upload("alice", _file(b"%PDF", "application/pdf", "report.pdf"), None)

    assert attachment.type == "unknown"
    assert attachment.mime_type == "application/pdf"


@pytest.mark.asyncio
async def test_a_pdf_keeps_the_size_of_its_pages_on_the_attachment(uploading):
    with _measured(DOCUMENT_META):
        attachment = await process_upload("alice", _file(b"%PDF", "application/pdf", "report.pdf"), None)

    assert (attachment.meta.original.width, attachment.meta.original.height) == (794, 1123)


@pytest.mark.asyncio
async def test_a_pdf_gets_no_rendered_preview(uploading, fake_media_storage):
    with _measured(DOCUMENT_META):
        attachment = await process_upload("alice", _file(b"%PDF", "application/pdf", "report.pdf"), None)

    assert attachment.preview_url is None


@pytest.mark.asyncio
async def test_a_pdf_we_cannot_measure_keeps_its_page_count(uploading):
    pages_only = DocumentMeta(pages=7)

    with _measured(pages_only):
        attachment = await process_upload("alice", _file(b"%PDF", "application/pdf", "report.pdf"), None)

    assert attachment.meta is None
    assert uploading.topic("media").published[0]["payload"]["metadata"]["pages"] == 7


@pytest.mark.asyncio
async def test_the_filename_travels_with_the_uploaded_object(uploading):
    with _measured(DOCUMENT_META):
        attachment = await process_upload("alice", _file(b"%PDF", "application/pdf", "Jahresbericht.pdf"), None)

    assert attachment.filename == "Jahresbericht.pdf"
    assert uploading.topic("media").published[0]["payload"]["filename"] == "Jahresbericht.pdf"


@pytest.mark.asyncio
async def test_an_upload_without_a_filename_carries_none(uploading):
    attachment = await process_upload("alice", _file(filename=""), None)

    assert attachment.filename is None
    assert "filename" not in uploading.topic("media").published[0]["payload"]


@pytest.mark.asyncio
async def test_an_animated_gif_keeps_the_mastodon_name_for_it(uploading):
    frames = io.BytesIO()
    Image.new("P", (10, 10)).save(frames, format="GIF", save_all=True,
                                  append_images=[Image.new("P", (10, 10))])

    attachment = await process_upload("alice", _file(frames.getvalue(), "image/gif", "loop.gif"), None)

    assert attachment.type == "gifv"

