# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from contextlib import asynccontextmanager
from profed.core.message_bus import message_bus, CatchUp
from profed.topics import media as media_topic


logger = logging.getLogger(__name__)


@asynccontextmanager
async def reading_media_state(source_urls: frozenset):
    state: dict = {}
    catch_up = CatchUp()
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

    def update_deleted(file_id):
        nonlocal state

        for src, entry in list(state.items()):
            if entry.get("file_id") == file_id:
                del state[src]

    async def _update() -> None:
        nonlocal state

        async for _, event_type, object_id, _, payload in \
                message_bus().topic("media").subscribe(start_id,
                                                       caught_up=catch_up.event):
            validated = media_topic["validate"](event_type, payload)
            if validated is None:
                continue

            if event_type == "uploaded":
                update_uploaded({**validated, "file_id": object_id})
            elif event_type == "deleted":
                update_deleted(object_id)

    task = asyncio.create_task(_update())
    catch_up.watch(task)
    try:
        yield state, catch_up
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
