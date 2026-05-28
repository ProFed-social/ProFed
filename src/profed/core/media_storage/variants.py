# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import io
from typing import Awaitable, Callable, Optional
from PIL import Image
from profed.core.media_storage import media_storage


OnComplete = Callable[[str, str, int, int, str], Awaitable[None]]


async def scale_image(media_id:    str,
                      variant:     str,
                      *,
                      width:       Optional[int]      = None,
                      height:      Optional[int]      = None,
                      on_complete: Optional[OnComplete] = None) -> tuple[int, int]:
    if width is None and height is None:
        raise ValueError("scale_image: at least one of width, height must be set")
    storage  = media_storage()
    (scaled,
     final_w,
     final_h,
     content_type) = await asyncio.to_thread(_scale_pillow,
                                             await storage.retrieve(media_id),
                                             width,
                                             height)
    await storage.store(f"{media_id}_{variant}", scaled, content_type)

    if on_complete is not None:
        await on_complete(media_id, variant, final_w, final_h, content_type)

    return final_w, final_h


def _scale_pillow(image_bytes, width, height):
    img    = Image.open(io.BytesIO(image_bytes))
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
             format=(fmt_in if fmt_in in ("JPEG", "PNG", "WEBP") else "JPEG"),
             **({"quality": 85} if fmt_out in ("JPEG", "WEBP") else {}))

    return (buf.getvalue(),
            width,
            height,
            {"JPEG": "image/jpeg",
             "PNG":  "image/png",
             "WEBP": "image/webp"}[fmt_out])
