# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import timeline
from profed.components.api.c2s.v1.timelines.storage import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


async def _store(username: str, status_id: str, actor_url: str, status: dict) -> None:
    await (await storage()).add(username, status_id, status["id"], actor_url, status)


async def _apply_item(data: dict) -> None:
    await _store(data["username"], data["status_id"], data.get("actor_url", ""), data["status"])


async def _on_store(object_id: str, payload: dict) -> None:
    await _store(payload["username"], payload["status_id"], payload.get("actor_url", ""), payload["status"])


async def _on_update(object_id: str, payload: dict) -> None:
    await (await storage()).update_status(payload["username"], payload["status_id"], payload["status"])


async def _on_delete(object_id: str, payload: dict) -> None:
    await (await storage()).delete_status(payload["username"], payload["status_id"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=timeline,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"Create": _on_store,
                                      "Update": _on_update,
                                      "Delete": _on_delete,
                                      "Announce": _on_store})

