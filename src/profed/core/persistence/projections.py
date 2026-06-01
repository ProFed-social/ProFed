# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from typing import Optional, Dict, Callable, Awaitable, Tuple, Any
from profed.core.message_bus import message_bus, TICK, CatchUp


class _EventHandlerSignature:
    def __init__(self,
                 *,
                 include_event_type: bool = False,
                 include_emitted_at: bool = False,
                 include_sequence_id: bool = False):
        self._include_event_type = include_event_type
        self._include_emitted_at = include_emitted_at
        self._include_sequence_id = include_sequence_id

    def __and__(self,
                other: "_EventHandlerSignature") -> "_EventHandlerSignature":
        return _EventHandlerSignature(
            include_event_type=self._include_event_type or other._include_event_type,
            include_emitted_at=self._include_emitted_at or other._include_emitted_at,
            include_sequence_id=self._include_sequence_id or other._include_sequence_id)

    async def __call__(self,
                       handler:    Callable[..., Awaitable[None]],
                       event_type: str,
                       object_id:  str,
                       emitted_at: Any,
                       sequence_id: int,
                       payload:    Dict) -> None:
        args = []
        if self._include_event_type:
            args.append(event_type)
        args.extend([object_id, payload])
        if self._include_emitted_at:
            args.append(emitted_at)
        if self._include_sequence_id:
            args.append(sequence_id)

        await handler(*args)


standard = _EventHandlerSignature()
with_event_type = _EventHandlerSignature(include_event_type=True)
with_emitted_at = _EventHandlerSignature(include_emitted_at=True)
with_sequence_id = _EventHandlerSignature(include_sequence_id=True)


def build_projection(topic: Dict,
                     subscriber: str,
                     init: Callable[[], Awaitable[None]],
                     on_message_type: Dict[str, Callable[..., Awaitable[None]]],
                     on_snapshot_item: Callable[[Dict], Awaitable[None]],
                     verify_event: Optional[Callable[[str, Dict], bool]] = None,
                     verify_snapshot_item: Optional[Callable[[Dict], bool]] = None,
                     event_handler_signature: _EventHandlerSignature = standard) \
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


    async def _dispatch(sequence_id, event_type, object_id, emitted_at, payload):
        if event_type not in on_message_type:
            return

        def _get_validated():
            validated = topic["validate"](event_type, payload)
            return (validated
                    if validated is not None and
                       verify_event(event_type, validated) else
                    None)

        validated = (payload
                     if event_type == TICK else
                     _get_validated())
        if validated is not None:
            await event_handler_signature(on_message_type[event_type],
                                          event_type,
                                          object_id,
                                          emitted_at,
                                          sequence_id,
                                          validated)

    async def handle_events():
        async for sequence_id, event_type, object_id, emitted_at, payload \
                in message_bus().topic(topic_name).subscribe(subscriber, last_seen):
            await _dispatch(sequence_id, event_type, object_id, emitted_at, payload)

    async def rebuild():
        nonlocal last_seen
        await init()
        last_seen, snapshot = await message_bus().topic(topic_name).last_snapshot()
        for it in snapshot:
            item = topic["snapshot_validate"](it)
            if item is not None and verify_snapshot_item(item):
                await on_snapshot_item(item)

        catch_up = CatchUp()
        async def _drain():
            nonlocal last_seen

            async for sequence_id, event_type, object_id, emitted_at, payload \
                    in message_bus().topic(topic_name).subscribe(subscriber,
                                                                 last_seen,
                                                                 caught_up=catch_up.event):
                await _dispatch(sequence_id, event_type, object_id, emitted_at, payload)
                last_seen = sequence_id
                if catch_up.event.is_set():
                    return

        drain_task = catch_up.watch(asyncio.create_task(_drain()))
        await catch_up.wait()
        drain_task.cancel()
        try:
            await drain_task
        except asyncio.CancelledError:
            pass

    def reset_last_seen(new_last_seen):
        nonlocal last_seen
        last_seen = new_last_seen

    return handle_events, rebuild, reset_last_seen

