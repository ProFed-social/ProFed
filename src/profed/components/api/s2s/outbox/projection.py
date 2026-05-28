# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.persistence.projections import build_projection, with_event_type
from profed.topics import activities
from profed.components.api.s2s.outbox.storage import storage


_ALL_AP_VERBS = ("Create", "Update", "Delete", "Follow", "Accept",
                 "Reject", "Undo", "Like", "Announce", "Block")


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()


async def _apply_item(data: dict) -> None:
    store = await storage()
    await store.add(data["username"], data["activity"])

async def _store_activity(event_type: str,
                          object_id:  str,
                          payload:    dict) -> None:
    await (await storage()).add(payload["username"],
                                {"id": object_id,
                                 "type": event_type,
                                 **payload["activity"]})


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=activities,
                         subscriber="api",
                         init=_init,
                         on_snapshot_item=_apply_item,
                         on_message_type={verb: _store_activity
                                          for verb in _ALL_AP_VERBS},
                         event_handler_signature=with_event_type)

