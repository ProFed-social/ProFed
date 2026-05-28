# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import media
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _uploaded(object_id: str, payload: dict) -> None:
    await (await storage()).insert(file_id=object_id,
                                   url=payload["url"],
                                   preview_url=payload.get("preview_url"),
                                   content_type=payload["content_type"],
                                   size=payload["size"],
                                   uploader=payload["uploader"],
                                   source_url=payload.get("source_url"),
                                   content_hash=payload.get("content_hash"),
                                   last_modified=payload.get("last_modified"),
                                   etag=payload.get("etag"),
                                   width=payload.get("width"),
                                   height=payload.get("height"),
                                   preview_width= payload.get("preview_width"),
                                   preview_height=payload.get("preview_height"))


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(object_id)


async def _uploaded_snapshot(item: dict) -> None:
    await (await storage()).insert(**{k: item.get(k)
                                      for k in ("file_id",
                                                "url",
                                                "preview_url",
                                                "content_type",
                                                "size",
                                                "uploader",
                                                "source_url",
                                                "content_hash",
                                                "last_modified",
                                                "etag",
                                                "width",
                                                "height",
                                                "preview_width",
                                                "preview_height")})


handle_events, rebuild, _ = build_projection(topic=media,
                                             subscriber="api_c2s_media",
                                             init=_init,
                                             on_snapshot_item=_uploaded_snapshot,
                                             on_message_type={"uploaded": _uploaded,
                                                              "deleted": _deleted})
