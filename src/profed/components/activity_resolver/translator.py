# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from urllib.parse import urlparse
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import (build_projection,
                                                 with_event_type,
                                                 with_sequence_id)
from profed.topics import incoming_activities
from profed.components.activity_resolver.resolve import resolve_object


_SOURCE = source_key("incoming_activities")


async def _noop() -> None:
    pass


async def _noop_item(item: dict) -> None:
    pass


def _actor_host(activity):
    actor = activity.get("actor")
    actor_id = actor.get("id") if isinstance(actor, dict) else actor
    return urlparse(actor_id).hostname if actor_id else None


def _forwarder(should_resolve: bool):
    async def _resolve_actually(activity):
        return {**activity, "object": await resolve_object(activity.get("object"),_actor_host(activity))}

    async def _resolve_nothing(activity):
        return activity

    _resolve = _resolve_actually if should_resolve else _resolve_nothing

    async def _publish_if_not_exists(topic, event_type, object_id, payload, message_id):
        if not await topic.exists(message_id):
            async with topic.publish() as publish:
                await publish(event_type=event_type,
                              object_id=object_id,
                              payload={**payload, "activity": await _resolve(payload["activity"])},
                              message_id=message_id)


    async def _handle(event_type, object_id, payload, sequence_id) -> None:
        await _publish_if_not_exists(topic=message_bus().topic("resolved_activities", lookup_message_ids=True),
                                     event_type=event_type,
                                     object_id=object_id,
                                     payload=payload,
                                     message_id=_SOURCE.message_id(sequence_id))

    return _handle


handle_events, rebuild, _ = build_projection(topic=incoming_activities,
                                             subscriber="activity_resolver",
                                             init=_noop,
                                             on_snapshot_item=_noop_item,
                                             on_message_type={"Create":   _forwarder(True),
                                                              "Update":   _forwarder(True),
                                                              "Announce": _forwarder(True),
                                                              "Delete":   _forwarder(False)},
                                             event_handler_signature=(with_event_type & with_sequence_id))

