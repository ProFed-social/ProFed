# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from profed.core.message_bus.source_key import source_key
from .storage import storage
from .translator import publish_polished


logger = logging.getLogger(__name__)


def _payload_of(row) -> dict:
    return json.loads(row["payload"]) if isinstance(row["payload"], str) else row["payload"]


async def update_all_waiting(acct: str, sequence_id: int) -> int:
    store = await storage()
    rows = await store.waiting_for(acct)

    for row in rows:
        await publish_polished("Update",
                               row["object_id"],
                               _payload_of(row),
                               row["emitted_at"],
                               source_key(f"remote_actors|{row['url']}").message_id(sequence_id))

    return len(rows)

