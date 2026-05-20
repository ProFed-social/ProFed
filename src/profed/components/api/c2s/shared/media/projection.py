# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import media
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _uploaded(payload: dict) -> None:
    await (await storage()).insert(file_id=payload["file_id"],
                                   url=payload["url"],
                                   preview_url=payload.get("preview_url"),
                                   content_type=payload["content_type"],
                                   size=payload["size"],
                                   uploader=payload["uploader"],
                                   width=payload.get("width"),
                                   height=payload.get("height"),
                                   preview_width=payload.get("preview_width"),
                                   preview_height=payload.get("preview_height"))


async def _deleted(payload: dict) -> None:
    await (await storage()).delete(payload["file_id"])


handle_events, rebuild, _ = build_projection(topic=media,
                                             subscriber="api_c2s_media",
                                             init=_init,
                                             on_snapshot_item=_uploaded,
                                             on_message_type={"uploaded": _uploaded,
                                                              "deleted": _deleted})
