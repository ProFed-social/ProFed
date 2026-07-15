# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import accounts
from .storage import storage


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


async def _apply_snapshot_item(item: dict) -> None:
    await (await storage()).add(item["username"], item)


async def _created(object_id: str, payload: dict) -> None:
    await (await storage()).add(object_id, payload)


async def _updated(object_id: str, payload: dict) -> None:
    await (await storage()).add(object_id, payload)


async def _followers_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"followers_count": payload["count"]})


async def _following_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"following_count": payload["count"]})


async def _statuses_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(object_id, {"statuses_count": payload["count"]})


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_account_events, rebuild, reset_last_seen = \
    build_projection(topic=accounts,
                     subscriber="api_c2s_actor",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_snapshot_item,
                     on_message_type={"created":           _created,
                                      "updated":           _updated,
                                      "followers_changed": _followers_changed,
                                      "following_changed": _following_changed,
                                      "statuses_changed":  _statuses_changed,
                                      "deleted":           _deleted})

