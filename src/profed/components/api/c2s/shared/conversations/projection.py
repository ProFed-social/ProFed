# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection
from profed.topics import timeline
from profed.components.api.c2s.shared.conversations import storage


async def _init() -> None:
    await (await storage.storage()).ensure_schema()


async def _record(message_url: str, actor_url: str, status: dict) -> None:
    if status.get("visibility") != "direct":
        return
    await (await storage.storage()).record(message_url,
                                           status.get("in_reply_to_id"),
                                           status["created_at"],
                                           actor_url,
                                           [mention["url"] for mention in status.get("mentions", [])])


async def _apply_item(data: dict) -> None:
    await _record(data["status_id"], data.get("actor_url", ""), data["status"])


async def _on_store(object_id: str, payload: dict) -> None:
    await _record(payload["status_id"], payload.get("actor_url", ""), payload["status"])


async def _rebuild_finished() -> None:
    (await storage.storage()).rebuild_finished()


handle_events, rebuild, _ = \
    build_projection(topic=timeline,
                     init=_init,
                     rebuild_finished=_rebuild_finished,
                     on_snapshot_item=_apply_item,
                     on_message_type={"Create": _on_store})

