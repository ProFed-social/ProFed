# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from uuid import uuid4
from PIL import Image
from fastapi import HTTPException, UploadFile
from profed.core.media_storage import media_storage
from profed.core.message_bus import message_bus
from profed.identity import acct_from_username
from profed.models.mastodon import (MediaAttachment,
                                    MediaAttachmentMeta,
                                    MediaAttachmentMetadata)


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


MAX_SIZE_BYTES = 10 * 1024 * 1024


def _media_type(content_type: str) -> str:
    return "gifv" if "gif" in content_type else "image"


def _process_image(data: bytes,
                   content_type: str) -> tuple[int, int, bytes, int, int]:
    img    = Image.open(io.BytesIO(data))
    orig_w, orig_h = img.size

    if getattr(img, "is_animated", False):
        return orig_w, orig_h, data, orig_w, orig_h

    thumb = img.copy()
    thumb.thumbnail((400, 400), Image.LANCZOS)
    thumb_w, thumb_h = thumb.size

    buf    = io.BytesIO()
    fmt    = ("JPEG" if "jpeg" in content_type else
              "GIF"  if "gif"  in content_type else
              "WEBP" if "webp" in content_type else "PNG")
    kwargs = {"quality": 85} if fmt in ("JPEG", "WEBP") else {}
    thumb.save(buf, format=fmt, **kwargs)

    return orig_w, orig_h, buf.getvalue(), thumb_w, thumb_h


async def process_upload(username:    str,
                         file:        UploadFile,
                         description: str | None) -> MediaAttachment:
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="unsupported_media_type")

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="file_too_large")

    file_id  = str(uuid4()).replace("-", "")
    uploader = acct_from_username(username)

    orig_w, orig_h, thumb_data, thumb_w, thumb_h = _process_image(data,
                                                                    file.content_type)
    stored       = await media_storage().store(file_id,             data,       file.content_type)
    thumb_stored = await media_storage().store(f"{file_id}-small", thumb_data, file.content_type)

    async with message_bus().topic("media").publish() as publish:
        await publish({"type":    "uploaded",
                       "payload": {"file_id":        file_id,
                                   "url":            stored.url,
                                   "preview_url":    thumb_stored.url,
                                   "content_type":   file.content_type,
                                   "size":           stored.size,
                                   "uploader":       uploader,
                                   "width":          orig_w,
                                   "height":         orig_h,
                                   "preview_width":  thumb_w,
                                   "preview_height": thumb_h}})

    return MediaAttachment(
        id=          file_id,
        type=        _media_type(file.content_type),
        url=         stored.url,
        preview_url= thumb_stored.url,
        description= description,
        meta=        MediaAttachmentMetadata(
            original= MediaAttachmentMeta(width=orig_w,  height=orig_h),
            small=    MediaAttachmentMeta(width=thumb_w, height=thumb_h)))

