# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection
from profed.federation.refresh import due_at
from profed.topics import known_servers as topic
from profed.util import noop
from .storage import storage


_config = {}


def configure(config: dict) -> None:
    global _config
    _config = config


async def _discovered(object_id: str, payload: dict) -> None:
    await (await storage()).remember_host(object_id)


async def _checked(object_id: str, payload: dict) -> None:
    row = {"checked_at": datetime.fromisoformat(payload["checked_at"]),
           "stable_since": datetime.fromisoformat(payload["stable_since"]),
           "last_modified": payload.get("last_modified")}
    await (await storage()).record_check(object_id,
                                         row["checked_at"],
                                         row["stable_since"],
                                         due_at(row, _config, row["checked_at"]),
                                         payload.get("failures", 0),
                                         row["last_modified"],
                                         payload.get("etag"),
                                         payload.get("content_hash"))


async def _lost(object_id: str, payload: dict) -> None:
    await (await storage()).forget_host(object_id)


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={"discovered": _discovered,
                                                              "updated": _checked,
                                                              "unreachable": _checked,
                                                              "lost": _lost})

