# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_emitted_at, with_event_type, with_sequence_id
from profed.topics.statuses_topic import STATUS_VERBS, delete_event, status_event
from profed.topics import activities
from profed.util import noop


_ACTIVITIES_SOURCE = source_key("activities")


async def _publish(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    async with message_bus().topic("statuses").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=_ACTIVITIES_SOURCE.message_id(sequence_id))


async def _convert(event_type: str,
                   object_id: str,
                   payload: dict,
                   emitted_at: datetime,
                   sequence_id: int) -> None:
    event = status_event(event_type, object_id, payload, emitted_at, sequence_id, own=True)
    if event is not None:
        await _publish(event_type, object_id, event, sequence_id)


async def _convert_delete(event_type: str,
                          object_id: str,
                          payload: dict,
                          emitted_at: datetime,
                          sequence_id: int) -> None:
    event = delete_event(event_type, object_id, payload)
    if event is not None:
        await _publish(event_type, object_id, event, sequence_id)


handle_events, rebuild, _ = \
    build_projection(topic=activities,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={verb: (_convert_delete
                                             if verb == "Delete" else
                                             _convert)
                                      for verb in STATUS_VERBS},
                     event_handler_signature=with_event_type & with_emitted_at & with_sequence_id)

