# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection
from profed.topics import known_servers
from profed.util import noop
from .storage import storage


async def _observed(object_id: str, payload: dict) -> None:
    if payload["activity_type"] == "EmojiReact":
        await (await storage()).record_observation(object_id, datetime.fromisoformat(payload["observed_at"]))


async def _updated(object_id: str, payload: dict) -> None:
    await (await storage()).record_update(object_id,
                                          payload.get("software"),
                                          payload.get("features") or [],
                                          datetime.fromisoformat(payload["checked_at"]))


handle_events, rebuild, _ = build_projection(topic=known_servers,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"observed": _observed,
                                                              "updated": _updated})

