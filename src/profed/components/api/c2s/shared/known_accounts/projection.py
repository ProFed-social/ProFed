# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from profed.core.persistence.projections import build_projection
from profed.topics import known_accounts
from .storage import storage


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _store(account_id: int, account: dict) -> None:
    await (await storage()).upsert(account_id,
                                   account["acct"],
                                   account["url"],
                                   account,
                                   datetime.now(timezone.utc))


async def _created(object_id: str, payload: dict) -> None:
    await _store(int(object_id), payload)


async def _updated(object_id: str, payload: dict) -> None:
    await _store(int(object_id), payload)


async def _followers_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(int(object_id), {"followers_count": payload["count"]})


async def _following_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(int(object_id), {"following_count": payload["count"]})


async def _statuses_changed(object_id: str, payload: dict) -> None:
    await (await storage()).update(int(object_id), {"statuses_count": payload["count"]})


async def _deleted(object_id: str, payload: dict) -> None:
    await (await storage()).delete(int(object_id))


async def _snapshot(item: dict) -> None:
    await _store(int(item["id"]), item)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=known_accounts,
                                             init=_init,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=_snapshot,
                                             on_message_type={"created":           _created,
                                                              "updated":           _updated,
                                                              "followers_changed": _followers_changed,
                                                              "following_changed": _following_changed,
                                                              "statuses_changed":  _statuses_changed,
                                                              "deleted":           _deleted})

