# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timezone
from profed.core.message_bus import message_bus
from profed.core.persistence.projections import build_projection
from profed.topics import reaction_refresh
from profed.topics.reactions_resolution_topic import claim_id
from profed.util import noop
from . import worker
from .storage import storage


_config: dict = {}


def configure(config: dict) -> None:
    global _config
    _config = config


async def claim(object_url: str, collection_url: str, attempt: int) -> bool:
    async with message_bus().topic("reactions_resolution").publish() as publish:
        return await publish(event_type="attempting",
                             object_id=object_url,
                             payload={"object_url": object_url,
                                      "collection_url": collection_url,
                                      "attempt": attempt},
                             message_id=claim_id(object_url, attempt)) is not None


async def _on_requested(object_id: str, payload: dict) -> None:
    for row in await (await storage()).due(payload["object_urls"],
                                           datetime.now(timezone.utc),
                                           _config["lease"]):
        if await claim(row["object_url"], row["collection_url"], row["attempt"]):
            await worker.enqueue(row["object_url"], row["collection_url"], row["attempt"])


handle_events, rebuild, _ = build_projection(topic=reaction_refresh,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"requested": _on_requested})

