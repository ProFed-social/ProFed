# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import ClassVar

from .activity_streams import ActivityStreamsObject


class Note(ActivityStreamsObject):
    _base_context: ClassVar[list[str | dict[str, str]]] = \
            ["https://www.w3.org/ns/activitystreams",
             {"profed": "https://profed.social/ns#",
              "filename": "profed:filename"}]

    type: str = "Note"
    attributedTo: str
    content: str
    summary: str | None = None
    inReplyTo: str | None = None
    published: str
    attachment: list[dict] | None = None
    to: list[str] = ["https://www.w3.org/ns/activitystreams#Public"]
    tag: list[dict] = []
    cc: list[str] = []

