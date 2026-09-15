# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.persistence.projections import build_projection, with_emitted_at, with_event_type
from profed.topics import reactions_resolution
from profed.util import noop
from .storage import storage


def _due_at(payload: dict):
    return datetime.fromisoformat(payload["next_due_at"]) if payload.get("next_due_at") else None


async def _on_state(event_type: str, object_id: str, payload: dict, emitted_at: datetime) -> None:
    await (await storage()).record(payload["object_url"],
                                   event_type,
                                   emitted_at,
                                   _due_at(payload),
                                   payload.get("attempt", 0))


async def _rebuild_finished() -> None:
    (await storage()).rebuild_finished()


handle_events, rebuild, _ = build_projection(topic=reactions_resolution,
                                             init=noop,
                                             rebuild_finished=_rebuild_finished,
                                             on_snapshot_item=noop,
                                             on_message_type={state: _on_state
                                                              for state in ("attempting",
                                                                            "succeeded",
                                                                            "failed")},
                                             event_handler_signature=with_event_type & with_emitted_at)

