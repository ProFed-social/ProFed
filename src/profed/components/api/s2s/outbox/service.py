# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.identity import actor_url_from_username
from profed.components.api.s2s.outbox.models import OrderedCollection
from profed.components.api.s2s.outbox.storage import storage
from typing import Optional


async def resolve_outbox(username: str) -> OrderedCollection:
    obx_storage = await storage()
    activities = await obx_storage.fetch(username)

    return (OrderedCollection(id=f"{actor_url_from_username(username)}/outbox",
                              totalItems=0,
                              orderedItems=activities)
            if activities is not None else
            None)

 
def _tombstone(url: str, deleted_at) -> dict:
    return {"@context": "https://www.w3.org/ns/activitystreams",
            "id": url,
            "type": "Tombstone",
            "deleted": deleted_at.isoformat()}

 
async def resolve_note(username: str, note_id: str) -> Optional[dict]:
    url = f"{actor_url_from_username(username)}/notes/{note_id}"
    row = await (await storage()).latest_for_object(username, url)
 
    return (None
            if row is None else
            _tombstone(url, row["created_at"])
            if row["type"] == "Delete" else
            row["object"])

