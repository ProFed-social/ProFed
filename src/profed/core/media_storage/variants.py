# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import io
import subprocess
from typing import Awaitable, Callable, Optional
from PIL import Image
from profed.core.media_storage import media_storage


OnComplete = Callable[[str, str, int, int, str], Awaitable[None]]


def _transcode_baseline(image_bytes):
    try:
        result = subprocess.run(["jpegtran"], input=image_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as exc:
        raise OSError("scale_image: jpegtran not found; install libjpeg-progs to "
                      "handle arithmetic or progressive JPEGs") from exc

    if result.returncode != 0 or not result.stdout:
        raise OSError("scale_image: jpegtran could not transcode the image: " +
                      result.stderr.decode(errors="replace")[:200])

    return result.stdout


async def scale_image(media_id: str,
                      variant: str,
                      *,
                      width: Optional[int] = None,
                      height: Optional[int] = None,
                      on_complete: Optional[OnComplete] = None) -> tuple[int, int]:
    def scale_with_fallback(image_bytes, width, height):
        def scale_pillow(image_bytes, width, height):
            img = Image.open(io.BytesIO(image_bytes))
            if getattr(img, "is_animated", False):
                raise ValueError("scale_image: cannot scale animated images")

            width = width or round(img.width * (float(height) / float(img.height)))
            height = height or round(img.height * (float(width) / float(img.width)))

            fmt_in = img.format
            fmt_out = fmt_in if fmt_in in ("JPEG", "PNG", "WEBP") else "JPEG"

            img = img.convert("RGB" + ("A"
                                       if fmt_in == "PNG" and img.mode in ("RGBA", "LA", "P") else
                                       "")).resize((width, height), Image.LANCZOS)
            buf = io.BytesIO()
            img.save(buf,
                     format=fmt_out,
                     **({"quality": 85} if fmt_out in ("JPEG", "WEBP") else {}))

            return (buf.getvalue(), width, height, {"JPEG": "image/jpeg",
                                                    "PNG": "image/png",
                                                    "WEBP": "image/webp"}[fmt_out])

        try:
            return scale_pillow(image_bytes, width, height)
        except OSError:
            return scale_pillow(_transcode_baseline(image_bytes), width, height)

    if width is None and height is None:
        raise ValueError("scale_image: at least one of width, height must be set")
    storage = media_storage()
    (scaled,
     final_w,
     final_h,
     content_type) = await asyncio.to_thread(scale_with_fallback, await storage.retrieve(media_id), width, height)
    await storage.add_variant(media_id, variant, scaled, content_type)

    if on_complete is not None:
        await on_complete(media_id, variant, final_w, final_h, content_type)

    return final_w, final_h


async def box_image(media_id: str,
                    variant: str,
                    *,
                    edge: int,
                    on_complete: Optional[OnComplete] = None) -> tuple[int, int]:
    def box_with_fallback(image_bytes, edge):
        def box_pillow(image_bytes, edge):
            img = Image.open(io.BytesIO(image_bytes))
            if getattr(img, "is_animated", False):
                raise ValueError("box_image: cannot box animated images")

            width = edge if img.width >= img.height else max(1, round(img.width * edge / img.height))
            height = edge if img.height >= img.width else max(1, round(img.height * edge / img.width))

            canvas = Image.new("RGB", (edge, edge), (0, 0, 0))
            canvas.paste(img.convert("RGB").resize((width, height), Image.LANCZOS),
                         ((edge - width) // 2, (edge - height) // 2))

            buf = io.BytesIO()
            canvas.save(buf, format="JPEG", quality=85)

            return buf.getvalue(), "image/jpeg"

        try:
            return box_pillow(image_bytes, edge)
        except OSError:
            return box_pillow(_transcode_baseline(image_bytes), edge)

    storage = media_storage()
    boxed, content_type = await asyncio.to_thread(box_with_fallback, await storage.retrieve(media_id), edge)
    await storage.add_variant(media_id, variant, boxed, content_type)

    if on_complete is not None:
        await on_complete(media_id, variant, edge, edge, content_type)

    return edge, edge

