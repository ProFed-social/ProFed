# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Any

from .resume import Resume


class Account(BaseModel):
    id: str
    username: str
    acct: str
    display_name: str
    note: str = ""
    url: str
    avatar: str | None = None
    avatar_static: str | None = None
    header: str | None = None
    header_static: str | None = None
    locked: bool = False
    bot: bool = False
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    followers_count: int = 0
    following_count: int = 0
    statuses_count: int = 0
    emojis: list[Any] = Field(default_factory=list)
    fields: list[Any] = Field(default_factory=list)
    source: dict[str, Any] | None = None
    resume: Resume | None = None

    @classmethod
    def from_actor(cls,
                   actor: dict,
                   *,
                   acct: str,
                   account_id: str,
                   url: str,
                   created_at=None) -> "Account":
        username = acct.split("@")[0]
        icon  = actor.get("icon") or {}
        image = actor.get("image") or {}
        return cls(id=account_id,
                   username=username,
                   acct=acct,
                   display_name=actor.get("name") or username,
                   note=actor.get("summary") or "",
                   url=url,
                   avatar=icon.get("url") if isinstance(icon, dict) else None,
                   avatar_static=icon.get("url") if isinstance(icon, dict) else None,
                   header=image.get("url") if isinstance(image, dict) else None,
                   header_static=image.get("url") if isinstance(image, dict) else None,
                   locked=actor.get("manuallyApprovesFollowers", False),
                   bot=actor.get("type") == "Service",
                   **({"created_at": created_at.isoformat()}
                      if hasattr(created_at, "isoformat") else
                      {}))


class Relationship(BaseModel):
    id: str
    following: bool = False
    requested: bool = False
    followed_by: bool = False
    blocking: bool = False
    muting: bool = False
    domain_blocking: bool = False
    endorsed: bool = False
    note: str = ""


class Status(BaseModel):
    id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    in_reply_to_id: str | None = None
    in_reply_to_account_id: str | None = None
    sensitive: bool = False
    spoiler_text: str = ""
    visibility: str = "public"
    language: str | None = None
    uri: str = ""
    url: str = ""
    replies_count: int = 0
    reblogs_count: int = 0
    favourites_count: int = 0
    content: str = ""
    reblog: Any | None = None
    application: Any | None = None
    account: Account
    media_attachments: list[Any] = Field(default_factory=list)
    mentions: list[Any] = Field(default_factory=list)
    tags: list[Any] = Field(default_factory=list)
    emojis: list[Any] = Field(default_factory=list)
    card: Any | None = None
    poll: Any | None = None
    bookmarked: bool = False
    favourited: bool = False
    reblogged: bool = False
    muted: bool = False
    pinned: bool = False


class StatusContext(BaseModel):
    ancestors:   list[Status] = []
    descendants: list[Status] = []


class MediaAttachmentMeta(BaseModel):
    width:  int | None = None
    height: int | None = None


class MediaAttachmentMetadata(BaseModel):
    original: MediaAttachmentMeta | None = None
    small:    MediaAttachmentMeta | None = None


class MediaAttachment(BaseModel):
    id:          str
    type:        str = "image"
    url:         str
    preview_url: str | None = None
    remote_url:  str | None = None
    description: str | None = None
    blurhash:    str | None = None
    meta:        MediaAttachmentMetadata | None = None

