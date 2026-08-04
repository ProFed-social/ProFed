# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import (build_projection,
                                                 with_emitted_at,
                                                 with_event_type,
                                                 with_sequence_id)
from profed.topics import incoming_activities
from profed.http.signatures import make_sign
from profed.components.activity_resolver import fetcher
from profed.components.activity_resolver import instance_key
from profed.federation.references import flatten_references
from profed.util import noop


_SOURCE = source_key("incoming_activities")


def _signer():
    key = instance_key.signing_key()
    return make_sign(*key) if key else None


def _forwarder(should_resolve: bool):
    def _flatten(activity, emitted_at):
        return flatten_references(activity, emitted_at, _signer(), fetcher.enqueue)

    def _keep(activity, emitted_at):
        return activity

    _resolve = _flatten if should_resolve else _keep

    async def _publish_if_not_exists(topic, event_type, object_id, payload, emitted_at, message_id):
        if not await topic.exists(message_id):
            async with topic.publish() as publish:
                await publish(event_type=event_type,
                              object_id=object_id,
                              payload={**payload, "activity": _resolve(payload["activity"], emitted_at)},
                              message_id=message_id)


    async def _handle(event_type, object_id, payload, emitted_at, sequence_id) -> None:
        await _publish_if_not_exists(topic=message_bus().topic("resolved_activities", lookup_message_ids=True),
                                     event_type=event_type,
                                     object_id=object_id,
                                     payload=payload,
                                     emitted_at=emitted_at,
                                     message_id=_SOURCE.message_id(sequence_id))

    return _handle


handle_events, rebuild, _ = \
    build_projection(topic=incoming_activities,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={"Create":   _forwarder(True),
                                      "Update":   _forwarder(True),
                                      "Announce": _forwarder(True),
                                      "Delete":   _forwarder(False)},
                     event_handler_signature=with_event_type & with_emitted_at & with_sequence_id)

