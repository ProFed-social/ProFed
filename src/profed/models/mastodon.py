# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from pydantic import BaseModel, Field
from typing import Any


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

