# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from PIL import Image
from fastapi import HTTPException, UploadFile
from profed.core.media_storage import media_storage
from profed.media import scale_image
from profed.core.message_bus import message_bus
from profed.identity import acct_from_username
from profed.models import MediaObject, ImageMeta
from profed.models.mastodon import (MediaAttachment,
                                    MediaAttachmentMeta,
                                    MediaAttachmentMetadata)


ALLOWED_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
MAX_SIZE_BYTES = 10 * 1024 * 1024
PREVIEW_DIM = 400


def _media_type(content_type: str) -> str:
    return "gifv" if "gif" in content_type else "image"


def _preview_dimensions(orig_w: int, orig_h: int) -> tuple[int, int]:
    return ((PREVIEW_DIM, round(orig_h * PREVIEW_DIM / orig_w))
            if orig_w >= orig_h else
            (round(orig_w * PREVIEW_DIM / orig_h), PREVIEW_DIM))


async def process_upload(username: str,
                         file: UploadFile,
                         description: str | None) -> MediaAttachment: 
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="unsupported_media_type")

    data = await file.read()
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=422, detail="file_too_large")

    uploader = acct_from_username(username)

    img = Image.open(io.BytesIO(data))
    orig_w, orig_h = img.size
    is_animated = getattr(img, "is_animated", False)
    stored = await media_storage().store(data, file.content_type)

    if is_animated:
        preview_url = stored.url
        preview_w, preview_h = orig_w, orig_h
    else:
        preview_w, preview_h = _preview_dimensions(orig_w, orig_h)
        preview_url = media_storage().url_for(stored.file_id, "small")

    async with message_bus().topic("media").publish() as publish:
        await publish(event_type="uploaded",
                      object_id=stored.file_id,
                      payload=MediaObject(url=stored.url,
                                          content_type=file.content_type,
                                          size=stored.size,
                                          uploader=uploader,
                                          metadata=ImageMeta(width=orig_w,
                                                             height=orig_h)).model_dump(exclude_none=True))

    if not is_animated:
        scale_image(stored.file_id,
                    "small",
                    **({"width":  PREVIEW_DIM} if orig_w >= orig_h else
                       {"height": PREVIEW_DIM}))

    return MediaAttachment(id=stored.file_id,
                           type=_media_type(file.content_type),
                           url=stored.url,
                           preview_url=preview_url,
                           description=description,
                           meta=MediaAttachmentMetadata(original=MediaAttachmentMeta(width=orig_w,
                                                                                     height=orig_h),
                                                        small=MediaAttachmentMeta(width=preview_w,
                                                                                  height=preview_h)))

