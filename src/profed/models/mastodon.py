# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Any

from .resume import Resume
from profed.identity import account_id
from profed.sanitize import sanitize_html


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
                   url: str,
                   created_at=None) -> "Account":
        username = acct.split("@")[0]

        icon  = actor.get("icon", {}).get("url") if isinstance(actor.get("icon"), dict) else None
        image = actor.get("image", {}).get("url") if isinstance(actor.get("image"), dict) else None
        resume = actor.get("resume")

        raw_created = created_at if created_at is not None else actor.get("published")
        created = (raw_created.isoformat()
                   if hasattr(raw_created, "isoformat") else
                   raw_created)

        return cls(id=account_id(acct),
                   username=username,
                   acct=acct,
                   display_name=actor.get("name") or username,
                   note=sanitize_html(actor.get("summary")) or "",
                   url=url,
                   avatar=icon,
                   avatar_static=icon,
                   header=image,
                   header_static=image,
                   locked=actor.get("manuallyApprovesFollowers", False),
                   bot=actor.get("type") == "Service",
                   resume=Resume.model_validate(resume) if resume else None,
                   **({"created_at": created} if created is not None else {}))


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


def _mention_object(acct: str, url: str) -> dict:
    return {"id": account_id(acct),
            "username": acct.split("@")[0],
            "url": url,
            "acct": acct}


def mentions_from_tag(tag: list) -> list[dict]:
    return [_mention_object(entry["name"].lstrip("@"), entry.get("href", ""))
            for entry in tag
            if isinstance(entry, dict) and entry.get("type") == "Mention" and entry.get("name")]


def tags_from_tag(tag: list) -> list[dict]:
    return [{"name": entry["name"].lstrip("#"), "url": entry.get("href", "")}
            for entry in tag
            if isinstance(entry, dict) and entry.get("type") == "Hashtag" and entry.get("name")]


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

    @classmethod
    def from_activity(cls, activity: dict, *, id: str, account: "Account | None" = None) -> "Status":
        def get_obj(activity):
            o = activity.get("object", {})
            return {} if isinstance(o, str) else o
 
        def default_account(actor_url):
            username = actor_url.rstrip("/").split("/")[-1]
            return Account(id="0", username=username, acct=actor_url, display_name=username, url=actor_url)

        def create_status(cls, id, account, activity, obj):
            tag = obj.get("tag", [])
            return cls(id=id,
                       account=account,
                       created_at=obj.get("published", "1970-01-01T00:00:00.000Z"),
                       uri=activity.get("id", ""),
                       url=obj.get("url", activity.get("id", "")),
                       content=obj.get("content", ""),
                       mentions=mentions_from_tag(tag),
                       tags=tags_from_tag(tag))

        return create_status(cls=cls,
                             id=id,
                             account=account or default_account(actor_url=activity.get("actor", "")),
                             activity=activity,
                             obj=get_obj(activity))


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

