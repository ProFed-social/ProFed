# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import io
from pathlib import Path
from PIL import Image
from fastapi import HTTPException, UploadFile
from profed.core.config import config
from profed.core.media_storage import media_storage
from profed.media import scale_image
from profed.core.message_bus import message_bus
from profed.identity import acct_from_username
from profed.models import ImageMeta, MediaKind, MediaObject
from profed.sanitize import strip_tags
from profed.models.mastodon import (MediaAttachment,
                                    MediaAttachmentMeta,
                                    MediaAttachmentMetadata)
from .probe import measured, preview_dimension


ACCEPTED = {"image/jpeg",
            "image/png",
            "image/gif",
            "image/webp",
            "video/mp4",
            "video/webm",
            "video/ogg",
            "video/quicktime",
            "audio/mpeg",
            "audio/mp4",
            "audio/ogg",
            "audio/opus",
            "audio/flac",
            "audio/wav",
            "audio/x-wav",
            "application/pdf"}


def supported_types() -> set[str]:
    return set(ACCEPTED)


def max_media_attachments() -> int:
    return config()["api"]["max_media_attachments"]


def size_limit(kind: MediaKind) -> int:
    return config()["api"][f"{kind.value}_size_limit"]


def as_type(content_type: str) -> str:
    kind = MediaKind.of(content_type)

    return kind.as_type if kind else MediaKind.document.as_type


async def process_upload(username: str, file: UploadFile, description: str | None) -> MediaAttachment:
    def accepted() -> MediaKind:
        kind = MediaKind.of(file.content_type) if file.content_type in ACCEPTED else None
        if kind is None:
            raise HTTPException(status_code=422, detail="unsupported_media_type")

        return kind

    def within_limit(data: bytes, kind: MediaKind) -> bytes:
        if len(data) > size_limit(kind):
            raise HTTPException(status_code=422, detail="file_too_large")

        return data

    def described(width=None, height=None, duration=None) -> MediaAttachmentMetadata:
        def fitted():
            edge = preview_dimension()

            return (MediaAttachmentMeta(width=edge, height=round(height * edge / width))
                    if width >= height else
                    MediaAttachmentMeta(width=round(width * edge / height), height=edge))

        return MediaAttachmentMetadata(original=MediaAttachmentMeta(width=width,
                                                                    height=height,
                                                                    duration=duration),
                                       small=fitted() if width and height else None)

    async def picture(file_id: str, data: bytes):
        image = Image.open(io.BytesIO(data))
        width, height = image.size

        if getattr(image, "is_animated", False):
            return ImageMeta(width=width, height=height), media_storage().url_for(file_id)

        scale_image(file_id,
                    "small",
                    **({"width": preview_dimension()} if width >= height else {"height": preview_dimension()}))

        return ImageMeta(width=width, height=height), media_storage().url_for(file_id, "small")

    async def probed(file_id: str, data: bytes, kind: MediaKind):
        metadata, poster = await measured(data, kind, Path(file.filename or "").suffix or ".bin")
        if poster is None:
            return metadata, None

        await media_storage().add_variant(file_id, "small", poster, "image/jpeg")

        return metadata, media_storage().url_for(file_id, "small")

    def shaped(metadata) -> MediaAttachmentMetadata | None:
        measures = metadata.model_dump()

        return (described(measures.get("width"), measures.get("height"), measures.get("duration"))
                if measures.get("width") or measures.get("duration") else
                None)

    def mastodon_type(kind: MediaKind) -> str:
        return "gifv" if kind is MediaKind.image and "gif" in file.content_type else kind.mastodon_type

    async def publish_and_return(kind):
        async def with_data(kind, data):
            async def with_stored(kind, data, stored):
                async def with_metadata(kind, data, stored, metadata, preview_url):
                    async with message_bus().topic("media").publish() as publish:
                        await publish(event_type="uploaded",
                                      object_id=stored.file_id,
                                      payload=MediaObject(url=stored.url,
                                                          content_type=file.content_type,
                                                          size=stored.size,
                                                          uploader=acct_from_username(username),
                                                          filename=file.filename or None,
                                                          description=strip_tags(description),
                                                          metadata=metadata).model_dump(exclude_none=True))

                    return MediaAttachment(id=stored.file_id,
                                           type=mastodon_type(kind),
                                           url=stored.url,
                                           preview_url=preview_url,
                                           mime_type=file.content_type,
                                           filename=file.filename or None,
                                           description=strip_tags(description),
                                           meta=shaped(metadata) if metadata else None)

                return await with_metadata(kind,
                                           data,
                                           stored,
                                           *(await (picture(stored.file_id, data)
                                                    if kind is MediaKind.image else
                                                    probed(stored.file_id, data, kind))))

            return await with_stored(kind, data, await media_storage().store(data, file.content_type))
        return await with_data(kind, within_limit(await file.read(), kind))

    return await publish_and_return(kind=accepted())

