# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import bookmarks
from profed.components.api.c2s.shared.bookmarks import storage


async def _init() -> None:
    await (await storage.storage()).ensure_schema()


async def _on_added(object_id: str, payload: dict, sequence_id: int) -> None:
    await (await storage.storage()).add(payload["actor_url"], payload["object_url"], sequence_id)


async def _on_removed(object_id: str, payload: dict, sequence_id: int) -> None:
    await (await storage.storage()).remove(payload["actor_url"], payload["object_url"])


async def _apply_item(data: dict) -> None:
    await (await storage.storage()).add(data["actor_url"], data["object_url"], data.get("marked_at", 0))


async def _rebuild_finished() -> None:
    (await storage.storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=bookmarks,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"added": _on_added,
                                      "removed": _on_removed},
                     event_handler_signature=with_sequence_id)

