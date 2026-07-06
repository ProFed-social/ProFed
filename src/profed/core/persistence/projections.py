# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
from typing import Optional, Dict, Callable, Awaitable, Tuple, Any
from profed.core.message_bus import message_bus, TICK, CatchUp
from profed.core.message_bus.source_key import source_key


logger = logging.getLogger(__name__)


def _identity(payload):
    return payload


_default_sanitize = _identity
_default_correction_verb_map = {}


def configure_defaults(sanitize=None, correction_verb_map=None):
    global _default_sanitize, _default_correction_verb_map
    if sanitize is not None:
        _default_sanitize = sanitize
    if correction_verb_map is not None:
        _default_correction_verb_map = correction_verb_map
 

async def _no_rebuild_finished() -> None:
    pass

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
                     event_handler_signature: _EventHandlerSignature = standard,
                     rebuild_finished: Callable[[], Awaitable[None]] = _no_rebuild_finished) \
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
 
    async def _heal(sequence_id, event_type, object_id, payload):
        verb = topic.get("correction_verb_map",
                         _default_correction_verb_map).get(event_type,
                                                           event_type)
        if verb is None:
            return

        async with message_bus().topic(topic_name).publish() as publish:
            written = await publish(event_type=verb,
                                    object_id=object_id,
                                    payload=payload,
                                    message_id=source_key(topic_name).message_id(sequence_id))

        if written is not None:
            logger.warning("second line healed unsanitised content: topic=%s type=%s id=%s",
                           topic_name, event_type, object_id)

    async def _dispatch(sequence_id, event_type, object_id, emitted_at, payload):
        if event_type not in on_message_type:
            return

        async def _get_validated_and_sanitized():
            validated = topic["validate"](event_type, payload)
            if validated is None or not verify_event(event_type, validated):
                return None 

            sanitized = topic.get("sanitize", _identity)(validated)
            if sanitized != validated:
                await _heal(sequence_id, event_type, object_id, sanitized)
            return sanitized

        payload = (payload
                   if event_type == TICK else
                   await _get_validated_and_sanitized())
        if payload is not None:
            await event_handler_signature(on_message_type[event_type],
                                          event_type,
                                          object_id,
                                          emitted_at,
                                          sequence_id,
                                          payload)

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

        await rebuild_finished()

    def reset_last_seen(new_last_seen):
        nonlocal last_seen
        last_seen = new_last_seen

    return handle_events, rebuild, reset_last_seen

