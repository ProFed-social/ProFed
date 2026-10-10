# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
import logging
import re
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from profed.core.config import config
from profed.models import AudioMeta, DocumentMeta, MediaKind, VideoMeta

logger = logging.getLogger(__name__)

PIXELS_PER_POINT = 96 / 72


def preview_dimension() -> int:
    return config()["api"]["preview_dimension"]


async def measured(data: bytes, kind: MediaKind, suffix: str) -> tuple:
    async def run(*command):
        try:
            process = await asyncio.create_subprocess_exec(*command,
                                                           stdout=asyncio.subprocess.PIPE,
                                                           stderr=asyncio.subprocess.PIPE)
        except FileNotFoundError:
            logger.warning("%s is not installed, media metadata stays incomplete", command[0])
            return None

        out, err = await process.communicate()
        if process.returncode != 0:
            logger.warning("%s failed: %s", command[0], err.decode(errors="replace").strip()[:200])
            return None

        return out

    @asynccontextmanager
    async def spilled(extension):
        with tempfile.TemporaryDirectory(prefix="profed-probe-") as directory:
            source = Path(directory) / f"source{extension}"
            source.write_bytes(data)
            yield source

    async def streams():
        async with spilled(suffix) as source:
            out = await run("ffprobe", "-v", "error", "-print_format", "json",
                            "-show_format", "-show_streams", str(source))
        try:
            return json.loads(out) if out else None
        except json.JSONDecodeError:
            logger.warning("ffprobe returned no usable JSON")
            return None

    def duration(probed):
        try:
            return round(float(probed.get("format", {})["duration"]), 3)
        except (KeyError, TypeError, ValueError):
            return None

    def visual(probed):
        return next((stream
                     for stream in probed.get("streams", [])
                     if stream.get("codec_type") == "video" and stream.get("width") and stream.get("height")),
                    None)

    async def poster():
        async with spilled(suffix) as source:
            target = source.with_name("poster.jpg")
            fitted = f"scale=w={preview_dimension()}:h={preview_dimension()}:force_original_aspect_ratio=decrease"
            produced = await run("ffmpeg", "-v", "error", "-i", str(source),
                                 "-vf", f"thumbnail,{fitted}", "-frames:v", "1", "-y", str(target))

            return target.read_bytes() if produced is not None and target.exists() else None

    async def video():
        probed = await streams()
        stream = visual(probed) if probed else None

        return ((VideoMeta(width=int(stream["width"]),
                           height=int(stream["height"]),
                           duration=duration(probed)), await poster())
                if stream else
                (None, None))

    async def audio():
        probed = await streams()

        return (AudioMeta(duration=duration(probed)) if probed else None), None

    async def document():
        def measure(info, pattern, scale=1):
            found = re.search(pattern, info, re.MULTILINE)

            return round(float(found.group(1)) * scale) if found else None

        async with spilled(".pdf") as source:
            out = await run("pdfinfo", str(source))

        if out is None:
            return None, None

        info = out.decode(errors="replace")

        return DocumentMeta(pages=measure(info, r"^Pages:\s+(\d+)"),
                            width=measure(info, r"^Page size:\s+([\d.]+) x", PIXELS_PER_POINT),
                            height=measure(info, r"^Page size:\s+[\d.]+ x ([\d.]+)", PIXELS_PER_POINT)), None

    async def nothing():
        return None, None

    return await {MediaKind.video: video,
                  MediaKind.audio: audio,
                  MediaKind.document: document}.get(kind, nothing)()

