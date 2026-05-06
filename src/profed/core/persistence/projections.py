# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import Optional, Dict, Callable, Awaitable, Tuple
from profed.core.message_bus import message_bus


def build_projection(topic: Dict,
                     subscriber: str,
                     init: Callable[[], Awaitable[None]],
                     on_message_type: Dict[str, Callable[[Dict], Awaitable[None]]],
                     on_snapshot_item: Callable[[Dict], Awaitable[None]],
                     verify_event: Optional[Callable[[str, Dict], bool]] = None,
                     verify_snapshot_item: Optional[Callable[[Dict], bool]] = None) \
        -> Tuple[Callable[[], Awaitable[None]],
                 Callable[[], Awaitable[None]],
                 Callable[[int], None]]:
    verify_event = (verify_event
                    if verify_event is not None else
                    lambda et, p: True)
    verify_snapshot_item = (verify_snapshot_item
                            if verify_snapshot_item is not None else
                            lambda i: True)
    last_seen = 0
    topic_name = topic["name"]

    async def handle_events():
        async for event in message_bus().topic(topic_name).subscribe(subscriber, last_seen):
            event_type, payload = topic["validate"](event)

            if (event_type is not None and
                event_type in on_message_type and
                verify_event(event_type, payload)):
                await on_message_type[event_type](payload)


    async def rebuild():
        nonlocal last_seen
        await init()
        last_seen, snapshot = await message_bus().topic(topic_name).last_snapshot()
        for it in snapshot:
            item = topic["snapshot_validate"](it)

            if item is not None and verify_snapshot_item(item):
                await on_snapshot_item(item)

        caught_up = asyncio.Event()
        async def _drain():
            nonlocal last_seen
            try:
                async for seq, event in \
                        message_bus().topic(topic_name).subscribe(subscriber,
                                                                  last_seen,
                                                                  include_sequence_id=True,
                                                                  caught_up=caught_up):
                    event_type, payload = topic["validate"](event)
                    if (event_type is not None and
                        event_type in on_message_type and
                        verify_event(event_type, payload)):
                            await on_message_type[event_type](payload)
                    last_seen = seq

                    if caught_up.is_set():
                        return
            except Exception:
                caught_up.set()
                raise

        drain_task = asyncio.create_task(_drain())
        await caught_up.wait()
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass


    def reset_last_seen(new_last_seen):
        nonlocal last_seen
        last_seen = new_last_seen

    return handle_events, rebuild, reset_last_seen
