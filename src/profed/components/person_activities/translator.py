# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import person
from profed.identity import actor_url_from_username
from profed.models.activity_pub import CreateActivity, UpdateActivity, DeleteActivity

logger = logging.getLogger(__name__)
_PERSON_SOURCE = source_key("person")


async def _init() -> None:
    pass


async def _apply_snapshot_item(item: dict) -> None:
    pass


async def _emit(username, activity, sequence_id) -> None:
    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type=activity.type,
                      object_id=activity.id,
                      payload={"username": username,
                               "activity": activity.as_event_payload()},
                      message_id=_PERSON_SOURCE.message_id(sequence_id))


async def _created(object_id, payload, sequence_id) -> None:
    actor_id = payload["id"]
    await _emit(object_id,
                CreateActivity(id=f"{actor_id}#create", actor=actor_id, object=payload),
                sequence_id)


async def _updated(object_id, payload, sequence_id) -> None:
    actor_id = payload["id"]
    await _emit(object_id,
                UpdateActivity(id=f"{actor_id}#update", actor=actor_id, object=payload),
                sequence_id)


async def _deleted(object_id, payload, sequence_id) -> None:
    actor_id = actor_url_from_username(object_id)
    await _emit(object_id,
                DeleteActivity(id=f"{actor_id}#delete", actor=actor_id, object=actor_id),
                sequence_id)


handle_person_events, rebuild, reset_last_seen = \
        build_projection(topic=person,
                         subscriber="person_activities",
                         init=_init,
                         on_snapshot_item=_apply_snapshot_item,
                         on_message_type={"created": _created,
                                          "updated": _updated,
                                          "deleted": _deleted},
                         event_handler_signature=with_sequence_id)

