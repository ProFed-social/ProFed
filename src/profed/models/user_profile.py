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
    public_key_pem: str | None = None
    private_key_pem: str | None = Field(default=None, exclude=True)
