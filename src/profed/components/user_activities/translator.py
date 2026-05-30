# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus, TICK
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import users
from profed.models import UserProfile
from profed.models.activity_pub import Person, CreateActivity, UpdateActivity, DeleteActivity
from .storage import storage

logger = logging.getLogger(__name__)
_USERS_SOURCE = source_key("users")


async def _init() -> None:
    await (await storage()).ensure_schema()


async def _apply_snapshot_item(item: dict) -> None:
    pass


async def _created(object_id, payload, sequence_id) -> None:
    await (await storage()).upsert_created(object_id,
                                           {**payload, "username": object_id},
                                           sequence_id)


async def _profile_edited(object_id, payload, sequence_id) -> None:
    await (await storage()).merge_change(object_id, payload, sequence_id)


async def _avatar_changed(object_id, payload, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"avatar_url": payload.get("url")}, sequence_id)


async def _header_changed(object_id, payload, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"header_url": payload.get("url")}, sequence_id)


async def _cv_changed(object_id, payload, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"resume": payload.get("resume")}, sequence_id)


async def _keys_generated(object_id, payload, sequence_id) -> None:
    await (await storage()).merge_change(object_id,
                                         {"public_key_pem": payload["public_key_pem"],
                                          "private_key_pem": payload["private_key_pem"]},
                                         sequence_id)


async def _deleted(object_id, payload, sequence_id) -> None:
    await (await storage()).mark_deleted(object_id, sequence_id)


def _activity_for(row, last_tick):
    actor = Person.from_user(UserProfile.model_validate(row["profile"]))

    if row["deleted_seq"] is not None:
        if row["created_seq"] > last_tick:
            return None
        return DeleteActivity(id=f"{actor.id}#delete", actor=actor.id, object=actor.id)

    cls, verb = ((CreateActivity, "create")
                 if row["created_seq"] > last_tick else
                 (UpdateActivity, "update"))

    return cls(id=f"{actor.id}#{verb}",
               actor=actor.id,
               object=actor.model_dump(by_alias=True, exclude_none=True))


async def _tick(object_id, payload, sequence_id) -> None:
    store     = await storage()
    last_tick = await store.last_tick_seq()

    for row in await store.pending_since(last_tick):
        activity = _activity_for(row, last_tick)
        if activity is not None:
            async with message_bus().topic("activities").publish() as publish:
                await publish(event_type=activity.type,
                              object_id=activity.id,
                              payload={"username": row["username"],
                                       "activity": activity.as_event_payload()},
                              message_id=_USERS_SOURCE.message_id(row["last_changed_seq"]))
        if row["deleted_seq"] is not None:
            await store.remove(row["username"])

    await store.set_last_tick_seq(sequence_id)


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=users,
                         subscriber="user_activities",
                         init=_init,
                         on_snapshot_item=_apply_snapshot_item,
                         on_message_type={"created": _created,
                                          "profile_edited": _profile_edited,
                                          "avatar_changed": _avatar_changed,
                                          "header_changed": _header_changed,
                                          "cv_changed": _cv_changed,
                                          "keys_generated": _keys_generated,
                                          "deleted": _deleted,
                                          TICK: _tick},
                         event_handler_signature=with_sequence_id)

