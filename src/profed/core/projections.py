# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional, Dict, Callable, Awaitable, Tuple
from profed.core.message_bus import message_bus


def build_projection(topic: Dict,
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
        async for event in message_bus().topic(topic_name).subscribe(last_seen):
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


    def reset_last_seen(new_last_seen):
        nonlocal last_seen
        last_seen = new_last_seen

    return handle_events, rebuild, reset_last_seen
