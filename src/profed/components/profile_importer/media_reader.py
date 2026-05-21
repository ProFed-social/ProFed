# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from contextlib import asynccontextmanager
from profed.core.message_bus import message_bus
from profed.topics import media as media_topic


logger = logging.getLogger(__name__)
_SUBSCRIBER = "profile_importer_media"


@asynccontextmanager
async def reading_media_state(source_urls: frozenset):
    state: dict = {}
    caught_up   = asyncio.Event()
    start_id, snapshot = await message_bus().topic("media").last_snapshot()

    for item in (snapshot or []):
        validated = media_topic["snapshot_validate"](item)
        if validated is not None and validated.get("source_url") in source_urls:
            state[validated["source_url"]] = validated

    def update_uploaded(payload):
        nonlocal state

        src = payload.get("source_url")
        if src in source_urls:
            state[src] = payload

    def update_deleted(payload):
        nonlocal state

        for src, entry in list(state.items()):
            if entry.get("file_id") == payload.get("file_id"):
                del state[src]

    async def _update() -> None:
        nonlocal state

        async for event in message_bus().topic("media").subscribe(_SUBSCRIBER,
                                                                  start_id,
                                                                  caught_up=caught_up):
            event_type, payload = media_topic["validate"](event)
            if payload is None:
                continue

            {"uploaded": update_uploaded,
             "deleted": update_deleted}.get(event_type,
                                            lambda p: p)(payload)

    task = asyncio.create_task(_update())
    try:
        yield state, caught_up
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
