# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
import asyncio
from typing import Optional, Dict, Callable, Awaitable, Tuple
from profed.core.message_bus import message_bus

logger = logging.getLogger(__name__)


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
        logger.debug("rebuild: starting init for topic %s", topic_name)
        await init()
        logger.debug("rebuild: init done, fetching last_snapshot for topic %s", topic_name)
        last_seen, snapshot = await message_bus().topic(topic_name).last_snapshot()
        logger.debug("rebuild: last_snapshot done, last_seen=%s, snapshot items=%s", last_seen, len(snapshot))
        for it in snapshot:
            item = topic["snapshot_validate"](it)

            if item is not None and verify_snapshot_item(item):
                await on_snapshot_item(item)

        logger.debug("rebuild: snapshot processed, creating drain task for topic %s", topic_name)
        caught_up = asyncio.Event()
        async def _drain():
            nonlocal last_seen
            logger.debug("rebuild: _drain starting for topic %s", topic_name)
            async for seq, event in message_bus().topic(topic_name).subscribe(subscriber,
                                                                              last_seen,
                                                                              include_sequence_id=True,
                                                                              caught_up=caught_up)
                logger.debug("rebuild: _drain got event %s for topic %s", seq, topic_name):
                event_type, payload = topic["validate"](event)
                if (event_type is not None and event_type in on_message_type and verify_event(event_type, payload)):
                    await on_message_type[event_type](payload)
                last_seen = seq
                if caught_up.is_set():
                    return

        logger.debug("rebuild: drain task created, waiting for caught_up for topic %s", topic_name)
        drain_task = asyncio.create_task(_drain())
        await caught_up.wait()
        logger.debug("rebuild: caught_up received for topic %s", topic_name)
        drain_task.cancel()
        try:
            await drain_task
            logger.debug("rebuild: drain task finished for topic %s", topic_name)
        except asyncio.CancelledError:
            logger.debug("rebuild: drain task cancelled for topic %s", topic_name)
            pass


    def reset_last_seen(new_last_seen):
        nonlocal last_seen
        last_seen = new_last_seen

    return handle_events, rebuild, reset_last_seen
