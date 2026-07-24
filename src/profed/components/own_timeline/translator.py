# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_event_type, with_sequence_id
from profed.topics import statuses
from profed.topics.statuses_topic import STATUS_VERBS
from profed.util import noop


_STATUSES_SOURCE = source_key("statuses")


async def _forward(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    async with message_bus().topic("timeline").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=_STATUSES_SOURCE.message_id(sequence_id))


handle_events, rebuild, _ = build_projection(topic=statuses,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: _forward for verb in STATUS_VERBS},
                                             event_handler_signature=with_event_type & with_sequence_id)

