# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional
from profed.core.persistence.projections import build_projection
from profed.topics import timeline as topic
from profed.util import noop
from .reactions_storage import storage


def _reaction(payload: dict) -> Optional[dict]:
    reference = payload.get("reference") or {}
    return (None
            if reference.get("kind") != "like" or not reference.get("url") else
            {"reaction_url": payload["status_id"],
             "object_url": reference["url"],
             "actor_url": payload.get("actor_url", ""),
             "emoji": reference.get("emoji") or "",
             "status_id": int(payload["status"]["id"])})


async def _on_react(object_id: str, payload: dict) -> None:
    row = _reaction(payload)
    if row is not None:
        await (await storage()).record(**row)


async def _on_delete(object_id: str, payload: dict) -> None:
    await (await storage()).forget(payload["status_id"])


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=topic,
                                             init=noop,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={"Like": _on_react,
                                                              "Delete": _on_delete})

