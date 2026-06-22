# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from asyncpg import ForeignKeyViolationError

from profed.core.persistence.projections import build_projection
from profed.topics import preferences as preferences_topic
from .storage import storage


logger = logging.getLogger(__name__)


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _updated(object_id: str, payload: dict) -> None:
    try:
        await (await storage()).upsert(object_id,
                                       payload.get("privacy"),
                                       payload.get("sensitive"),
                                       payload.get("language"))
    except ForeignKeyViolationError:
        logger.warning("Ignoring preferences event for %s: unknown language %r",
                       object_id,
                       payload.get("language"))


async def _snapshot(item: dict) -> None:
    await (await storage()).upsert(item["username"],
                                   item.get("privacy"),
                                   item.get("sensitive"),
                                   item.get("language"))


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, reset_last_seen = \
    build_projection(topic=preferences_topic,
                     subscriber="api_c2s_preferences",
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_snapshot,
                     on_message_type={"updated": _updated})

