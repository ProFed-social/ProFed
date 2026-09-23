# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from pydantic import ValidationError
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_event_type, with_sequence_id
from profed.topics import local_delivery
from profed.topics.incoming_activities_topic import _KNOWN_VERBS, canonical_incoming, publish_incoming
from profed.util import noop


logger = logging.getLogger(__name__)

_LOCAL_DELIVERY_SOURCE = source_key("local_delivery")


async def _deliver(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    try:
        verb, activity_id, canonical = canonical_incoming({"id": object_id,
                                                           "type": event_type,
                                                           **payload["activity"]})
    except ValidationError:
        logger.warning("local_delivery: dropping malformed %s %s", event_type, object_id)
    else:
        await publish_incoming(verb,
                               activity_id,
                               payload["username"],
                               canonical,
                               _LOCAL_DELIVERY_SOURCE.message_id(sequence_id))


handle_events, rebuild, _ = build_projection(topic=local_delivery,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: _deliver for verb in _KNOWN_VERBS},
                                             event_handler_signature=with_event_type & with_sequence_id)

