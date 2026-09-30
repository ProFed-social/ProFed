# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection
from profed.topics import me_links as topic
from profed.topics.me_links_topic import link_parts
from profed.util import noop
from .storage import init as init_storage, storage


async def init(config: dict) -> None:
    await init_storage(config)


async def _init() -> None:
    await (await storage()).ensure_schema()


def _checked(state: str):
    async def _record(object_id: str, payload: dict) -> None:
        actor_url, link_url = link_parts(object_id)
        await (await storage()).upsert(actor_url, link_url, state, datetime.fromisoformat(payload["checked_at"]))

    return _record


async def _deleted(object_id: str, payload: dict) -> None:
    actor_url, link_url = link_parts(object_id)
    await (await storage()).delete(actor_url, link_url)


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=_init,
                                             on_snapshot_item=noop,
                                             on_message_type={"verified": _checked("verified"),
                                                              "unverified": _checked("unverified"),
                                                              "gone": _checked("gone"),
                                                              "deleted": _deleted})

