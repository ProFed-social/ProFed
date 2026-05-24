# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, ConfigDict, Field
from .resume import Resume


class UserProfile(BaseModel):
    model_config = ConfigDict(extra="allow")

    username: str
    name: str | None = None
    summary: str | None = None
    resume: Resume | None = None
    avatar_source_url: str | None = None
    avatar_url: str | None = None
    avatar_small_url:  str | None = None
    header_source_url: str | None = None
    header_url: str | None = None
    public_key_pem: str | None = None
    private_key_pem: str | None = Field(default=None, exclude=True)

