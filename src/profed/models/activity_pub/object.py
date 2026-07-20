# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from .activity_streams import ActivityStreamsObject


class Note(ActivityStreamsObject):
    type: str = "Note"
    attributedTo: str
    content: str
    summary: str | None = None
    published: str
    to: list[str] = ["https://www.w3.org/ns/activitystreams#Public"]
    tag: list[dict] = []
    cc: list[str] = []

