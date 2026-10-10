# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import Enum
from typing import Annotated, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt


class MediaKind(str, Enum):
    image = "image"
    video = "video"
    audio = "audio"
    document = "document"

    @classmethod
    def of(cls, content_type: str) -> Optional["MediaKind"]:
        return (cls.document
                if content_type == "application/pdf" else
                cls.__members__.get((content_type or "").split("/")[0]))

    @classmethod
    def named(cls, as_type: str) -> Optional["MediaKind"]:
        return next((kind for kind in cls if kind.as_type == as_type), None)

    @property
    def as_type(self) -> str:
        return self.value.capitalize()

    @property
    def mastodon_type(self) -> str:
        return "unknown" if self is MediaKind.document else self.value


class ImageMeta(BaseModel):
    kind: Literal["image"] = "image"
    width: StrictInt
    height: StrictInt


class VideoMeta(BaseModel):
    kind: Literal["video"] = "video"
    width: StrictInt
    height: StrictInt
    duration: StrictFloat | None = None


class AudioMeta(BaseModel):
    kind: Literal["audio"] = "audio"
    duration: StrictFloat | None = None


class DocumentMeta(BaseModel):
    kind: Literal["document"] = "document"
    pages: StrictInt | None = None
    width: StrictInt | None = None
    height: StrictInt | None = None


MediaMeta = Annotated[Union[ImageMeta, VideoMeta, AudioMeta, DocumentMeta], Field(discriminator="kind")]


class MediaObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url:str
    content_type: str
    size: StrictInt
    uploader: str | None = None
    source_url: str | None = None
    content_hash: str | None = None
    last_modified: str | None = None
    etag: str | None = None
    filename: str | None = None
    description: str | None = None
    metadata: MediaMeta | None = None

