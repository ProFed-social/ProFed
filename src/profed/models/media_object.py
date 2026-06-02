# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from pydantic import BaseModel, ConfigDict, StrictInt


class MediaObject(BaseModel):
    model_config = ConfigDict(extra="allow")

    url:           str
    content_type:  str
    size:          StrictInt
    uploader:      str | None = None
    source_url:    str | None = None
    content_hash:  str | None = None
    last_modified: str | None = None
    etag:          str | None = None

