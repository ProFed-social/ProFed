# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
import os

import pytest
from unittest.mock import AsyncMock, patch

from profed.components.api.c2s.shared.media import probe
from profed.components.api.c2s.shared.media.probe import measured
from profed.models import MediaKind


VIDEO_PROBE = {"streams": [{"codec_type": "audio", "codec_name": "aac"},
                           {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080}],
               "format": {"duration": "12.3456"}}

AUDIO_PROBE = {"streams": [{"codec_type": "audio", "codec_name": "mp3"}],
               "format": {"duration": "2.038"}}

PDF_INFO = b"""Title:          Jahresbericht
Pages:          12
Page size:      595.276 x 841.89 pts (A4)
File size:      204800 bytes
"""


def _tools(**answers):
    def started(*command, **kwargs):
        answer = answers.get(command[0], b"")
        if callable(answer):
            answer = answer(command)

        process = AsyncMock()
        process.communicate = AsyncMock(return_value=(b"" if answer is None else answer, b"tool said no"))
        process.returncode = 1 if answer is None else 0

        return process

    return patch.object(asyncio, "create_subprocess_exec", AsyncMock(side_effect=started))


def _writing(payload):
    def written(command):
        open(command[command.index("-y") + 1], "wb").write(payload)
        return b""

    return written


def _json(payload):
    return json.dumps(payload).encode()


@pytest.fixture(autouse=True)
def a_preview_size(api_config):
    return api_config


@pytest.mark.asyncio
async def test_a_video_reports_the_dimensions_of_its_visual_stream():
    with _tools(ffprobe=_json(VIDEO_PROBE)):
        meta, _ = await measured(b"irrelevant", MediaKind.video, ".mp4")

    assert (meta.width, meta.height) == (1920, 1080)


@pytest.mark.asyncio
async def test_a_video_reports_its_duration_in_seconds():
    with _tools(ffprobe=_json(VIDEO_PROBE)):
        meta, _ = await measured(b"irrelevant", MediaKind.video, ".mp4")

    assert meta.duration == 12.346


@pytest.mark.asyncio
async def test_the_metadata_says_which_kind_it_describes():
    with _tools(ffprobe=_json(VIDEO_PROBE)):
        assert (await measured(b"irrelevant", MediaKind.video, ".mp4"))[0].kind == "video"

    with _tools(ffprobe=_json(AUDIO_PROBE)):
        assert (await measured(b"irrelevant", MediaKind.audio, ".mp3"))[0].kind == "audio"


@pytest.mark.asyncio
async def test_a_file_without_a_visual_stream_is_no_video():
    with _tools(ffprobe=_json(AUDIO_PROBE)):
        assert await measured(b"irrelevant", MediaKind.video, ".mp3") == (None, None)


@pytest.mark.asyncio
async def test_a_visual_stream_without_dimensions_is_no_video():
    without_size = {"streams": [{"codec_type": "video"}], "format": {"duration": "1.0"}}

    with _tools(ffprobe=_json(without_size)):
        assert await measured(b"irrelevant", MediaKind.video, ".mp4") == (None, None)


@pytest.mark.asyncio
async def test_an_audio_file_reports_its_duration():
    with _tools(ffprobe=_json(AUDIO_PROBE)):
        meta, _ = await measured(b"irrelevant", MediaKind.audio, ".mp3")

    assert meta.duration == 2.038


@pytest.mark.asyncio
async def test_an_audio_file_without_a_duration_still_yields_metadata():
    with _tools(ffprobe=_json({"streams": [{"codec_type": "audio"}], "format": {}})):
        meta, _ = await measured(b"irrelevant", MediaKind.audio, ".mp3")

    assert meta is not None
    assert meta.duration is None


@pytest.mark.asyncio
async def test_a_tool_that_fails_leaves_the_metadata_empty_instead_of_raising():
    with _tools(ffprobe=None):
        assert await measured(b"irrelevant", MediaKind.video, ".mp4") == (None, None)

    with _tools(ffprobe=None):
        assert await measured(b"irrelevant", MediaKind.audio, ".mp3") == (None, None)

    with _tools(pdfinfo=None):
        assert await measured(b"irrelevant", MediaKind.document, ".pdf") == (None, None)


@pytest.mark.asyncio
async def test_a_tool_that_is_not_installed_leaves_the_metadata_empty():
    with patch.object(asyncio, "create_subprocess_exec", AsyncMock(side_effect=FileNotFoundError)):
        assert await measured(b"irrelevant", MediaKind.video, ".mp4") == (None, None)


@pytest.mark.asyncio
async def test_unparsable_tool_output_leaves_the_metadata_empty():
    with _tools(ffprobe=b"this is not json"):
        assert await measured(b"irrelevant", MediaKind.video, ".mp4") == (None, None)


@pytest.mark.asyncio
async def test_a_document_reports_its_page_count():
    with _tools(pdfinfo=PDF_INFO):
        meta, _ = await measured(b"irrelevant", MediaKind.document, ".pdf")

    assert meta.pages == 12


@pytest.mark.asyncio
async def test_a_document_reports_its_page_size_in_pixels_not_points():
    with _tools(pdfinfo=PDF_INFO):
        meta, _ = await measured(b"irrelevant", MediaKind.document, ".pdf")

    assert (meta.width, meta.height) == (794, 1123)


@pytest.mark.asyncio
async def test_a_document_without_a_readable_page_size_still_yields_metadata():
    with _tools(pdfinfo=b"Pages:          3\n"):
        meta, _ = await measured(b"irrelevant", MediaKind.document, ".pdf")

    assert meta.pages == 3
    assert meta.width is None


@pytest.mark.asyncio
async def test_a_document_gets_no_poster():
    with _tools(pdfinfo=PDF_INFO):
        assert (await measured(b"irrelevant", MediaKind.document, ".pdf"))[1] is None


@pytest.mark.asyncio
async def test_the_poster_of_a_video_is_handed_back_as_image_data():
    with _tools(ffprobe=_json(VIDEO_PROBE), ffmpeg=_writing(b"poster bytes")):
        assert (await measured(b"irrelevant", MediaKind.video, ".mp4"))[1] == b"poster bytes"


@pytest.mark.asyncio
async def test_a_video_whose_poster_cannot_be_rendered_keeps_its_metadata():
    with _tools(ffprobe=_json(VIDEO_PROBE), ffmpeg=None):
        meta, poster = await measured(b"irrelevant", MediaKind.video, ".mp4")

    assert poster is None
    assert meta.width == 1920


async def test_the_poster_is_scaled_to_the_configured_preview_size():
    seen = []

    def remember(command):
        seen.append(" ".join(command))
        return b""

    with _tools(ffprobe=_json(VIDEO_PROBE), ffmpeg=remember):
        await measured(b"irrelevant", MediaKind.video, ".mp4")

    assert f"scale=w={probe.preview_dimension()}:h={probe.preview_dimension()}" in seen[0]


@pytest.mark.asyncio
async def test_an_image_needs_no_external_tool_at_all():
    with patch.object(asyncio, "create_subprocess_exec", AsyncMock(side_effect=AssertionError("no tool"))):
        assert await measured(b"irrelevant", MediaKind.image, ".png") == (None, None)



@pytest.mark.asyncio
async def test_the_probed_file_is_gone_once_the_probe_is_done():
    seen = []

    def remember(command):
        seen.append(command[-1])
        return _json(VIDEO_PROBE)

    with _tools(ffprobe=remember):
        await measured(b"irrelevant", MediaKind.video, ".mp4")

    assert seen and not os.path.exists(seen[0])

