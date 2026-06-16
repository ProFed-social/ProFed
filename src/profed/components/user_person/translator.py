# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus, TICK
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import (build_projection,
                                                 with_emitted_at,
                                                 with_sequence_id)
from profed.topics import users
from profed.models import UserProfile
from profed.models.activity_pub import Person
from .storage import storage

logger = logging.getLogger(__name__)
_USERS_SOURCE = source_key("users")


async def _init() -> None:
    store = await storage()
    await store.ensure_schema()
    store.rebuild_finished()

async def _apply_snapshot_item(item: dict) -> None:
    pass


async def _created(object_id, payload, emitted_at, sequence_id) -> None:
    profile = {k: v for k, v in payload.items() if k != "private_key_pem"}
    await (await storage()).upsert_created(object_id,
                                           {**profile, "username": object_id},
                                           emitted_at.isoformat(),
                                           sequence_id)


async def _profile_edited(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, payload, sequence_id)


async def _avatar_changed(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"avatar": payload or None}, sequence_id)


async def _header_changed(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"header": payload or None}, sequence_id)


async def _cv_changed(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id, {"resume": payload.get("resume")}, sequence_id)


async def _keys_generated(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).merge_change(object_id,
                                         {"public_key_pem": payload["public_key_pem"]},
                                         sequence_id)


async def _deleted(object_id, payload, emitted_at, sequence_id) -> None:
    await (await storage()).mark_deleted(object_id, sequence_id)


def _person_event_for(row, last_tick):
    if row["deleted_seq"] is not None:
        if row["created_seq"] > last_tick:
            return None
        return ("deleted", {})

    verb   = "created" if row["created_seq"] > last_tick else "updated"
    person = Person.from_user(UserProfile.model_validate(row["profile"]),
                              published=row["published"])

    return (verb, person.model_dump(by_alias=True, exclude_none=True))


async def _tick(object_id, payload, emitted_at, sequence_id) -> None:
    store = await storage()
    last_tick = await store.last_tick_seq()

    for row in await store.pending_since(last_tick):
        event = _person_event_for(row, last_tick)
        if event is not None:
            event_type, body = event
            async with message_bus().topic("person").publish() as publish:
                await publish(event_type=event_type,
                              object_id=row["username"],
                              payload=body,
                              message_id=_USERS_SOURCE.message_id(row["last_changed_seq"]))
        if row["deleted_seq"] is not None:
            await store.remove(row["username"])

    await store.set_last_tick_seq(sequence_id)


handle_user_events, rebuild, reset_last_seen = \
        build_projection(topic=users,
                         subscriber="user_person",
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
                         event_handler_signature=with_emitted_at & with_sequence_id)

