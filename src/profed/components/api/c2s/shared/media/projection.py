# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import media
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _store(file_id: str, source: dict) -> None:
    metadata = source.get("metadata") or {}
    await (await storage()).insert(file_id=file_id,
                                   url=source["url"],
                                   content_type=source["content_type"],
                                   size=source["size"],
                                   uploader=source["uploader"],
                                   source_url=source.get("source_url"),
                                   content_hash=source.get("content_hash"),
                                   last_modified=source.get("last_modified"),
                                   etag=source.get("etag"),
                                   width=metadata.get("width"),
                                   height=metadata.get("height"))


async def _uploaded(object_id: str, payload: dict) -> None:
    await _store(object_id, payload)


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(object_id)


async def _uploaded_snapshot(item: dict) -> None:
    await _store(item["file_id"], item)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=media,
                                             init=_init,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=_uploaded_snapshot,
                                             on_message_type={"uploaded": _uploaded,
                                                              "deleted": _deleted})

