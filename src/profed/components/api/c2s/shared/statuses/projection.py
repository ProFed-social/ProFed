# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import timeline
from profed.components.api.c2s.shared.statuses import as_objects, user_timeline


async def _init() -> None:
    await (await as_objects.storage()).ensure_schema()
    await (await user_timeline.storage()).ensure_schema()


def _edge(reference: dict | None) -> tuple[str, str | None]:
    return (("announce", reference["url"]) if reference and reference["kind"] == "announce" else ("content", None))


async def _store(username: str, url: str, actor_url: str, status: dict, reference: dict | None) -> None:
    await (await as_objects.storage()).upsert(status["id"], url, actor_url, status, *_edge(reference))
    await (await user_timeline.storage()).add(username, url, status["id"])


async def _apply_item(data: dict) -> None:
    await _store(data["username"],
                 data["status_id"],
                 data.get("actor_url", ""),
                 data["status"],
                 data.get("reference"))



async def _on_store(object_id: str, payload: dict) -> None:
    await _store(payload["username"],
                 payload["status_id"],
                 payload.get("actor_url", ""),
                 payload["status"],
                 payload.get("reference"))


async def _on_update(object_id: str, payload: dict) -> None:
    status = payload["status"]
    url = payload["status_id"]
    await (await as_objects.storage()).upsert(status["id"],
                                              url,
                                              payload.get("actor_url", ""),
                                              status,
                                              *_edge(payload.get("reference")))
    await (await as_objects.storage()).update_content(url, status, status.get("edited_at"))


async def _on_delete(object_id: str, payload: dict) -> None:
    url = payload["status_id"]
    await (await as_objects.storage()).delete(url)
    await (await user_timeline.storage()).remove_object(url)


async def _rebuild_finished() -> None:
    (await as_objects.storage()).rebuild_finished()
    (await user_timeline.storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=timeline,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"Create": _on_store,
                                      "Update": _on_update,
                                      "Delete": _on_delete,
                                      "Announce": _on_store})

