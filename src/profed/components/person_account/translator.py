# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import person, followers, activities
from profed.identity import acct_from_username, username_from_acct, domain
from profed.models.mastodon import Account
from .storage import storage


logger = logging.getLogger(__name__)
_PERSON_SOURCE = source_key("person")
_FOLLOWERS_SOURCE = source_key("followers")
_FOLLOWING_SOURCE = source_key("followers:following")
_ACTIVITIES_SOURCE = source_key("activities")

_ACTOR_TYPES = {"Person", "Service", "Group", "Organization", "Application"}


async def _noop() -> None:
    pass


async def _noop_item(item: dict) -> None:
    pass


async def _publish(event_type: str, object_id: str, payload: dict, message_id) -> None:
    async with message_bus().topic("accounts").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=message_id)


async def _emit_account(event_type: str, username: str, person_actor: dict, sequence_id: int) -> None:
    acct = acct_from_username(person_actor["preferredUsername"])
    account = Account.from_actor(person_actor, acct=acct, url=person_actor["id"])

    store = await storage()
    account.followers_count, account.following_count = await store.count_follows(acct)
    account.statuses_count = await store.count_statuses(username)

    await _publish(event_type,
                   username,
                   account.model_dump(),
                   _PERSON_SOURCE.message_id(sequence_id))


async def _person_created(object_id, payload, sequence_id) -> None:
    await _emit_account("created", object_id, payload, sequence_id)


async def _person_updated(object_id, payload, sequence_id) -> None:
    await _emit_account("updated", object_id, payload, sequence_id)


async def _person_deleted(object_id, payload, sequence_id) -> None:
    await _publish("deleted", object_id, {}, _PERSON_SOURCE.message_id(sequence_id))

handle_person_events, _, _ = \
    build_projection(topic=person,
                     subscriber="person_account_person",
                     init=_noop,
                     on_snapshot_item=_noop_item,
                     on_message_type={"created": _person_created,
                                      "updated": _person_updated,
                                      "deleted": _person_deleted},
                     event_handler_signature=with_sequence_id)


async def _emit_count(event_type: str, username: str, count: int, source, sequence_id: int) -> None:
    await _publish(event_type, username, {"count": count}, source.message_id(sequence_id))


def _is_local(acct: str) -> bool:
    return acct.rsplit("@", 1)[-1] == domain()


async def _emit_edge_change(follower: str, following: str, sequence_id: int) -> None:
    store = await storage()
    if _is_local(following):
        await _emit_count("followers_changed",
                          username_from_acct(following),
                          await store.count_followers(following),
                          _FOLLOWERS_SOURCE,
                          sequence_id)
    if _is_local(follower):
        await _emit_count("following_changed",
                          username_from_acct(follower),
                          await store.count_following(follower),
                          _FOLLOWING_SOURCE,
                          sequence_id)


async def _follower_accepted(object_id, payload, sequence_id) -> None:
    follower, following = object_id.split("|", 1)
    if await (await storage()).add_edge(follower, following):
        await _emit_edge_change(follower, following, sequence_id)


async def _follower_deleted(object_id, payload, sequence_id) -> None:
    follower, following = object_id.split("|", 1)
    if await (await storage()).remove_edge(follower, following):
        await _emit_edge_change(follower, following, sequence_id)


handle_followers_events, _, _ = \
    build_projection(topic=followers,
                     subscriber="person_account_followers",
                     init=_noop,
                     on_snapshot_item=_noop_item,
                     on_message_type={"accepted": _follower_accepted,
                                      "deleted": _follower_deleted},
                     event_handler_signature=with_sequence_id)


def _is_actor_object(activity: dict) -> bool:
    obj = activity.get("object")
    return isinstance(obj, dict) and obj.get("type") in _ACTOR_TYPES


def _is_actor_self_delete(activity: dict) -> bool:
    return activity.get("actor") is not None and activity.get("actor") == activity.get("object")


def _status_id(activity: dict):
    obj = activity.get("object")
    return obj.get("id") if isinstance(obj, dict) else obj


async def _apply_status(username: str, status_id, present: bool, sequence_id: int) -> None:
    if status_id is None:
        return

    store = await storage()
    changed = await (store.add_status if present else store.remove_status)(username, status_id)
    if changed:
        await _emit_count("statuses_changed", username,
                          await store.count_statuses(username), _ACTIVITIES_SOURCE, sequence_id)
 

async def _status_created(object_id, payload, sequence_id) -> None:
    if _is_actor_object(payload["activity"]):
        return
    await _apply_status(payload["username"], _status_id(payload["activity"]), True, sequence_id)


async def _status_announced(object_id, payload, sequence_id) -> None:
    await _apply_status(payload["username"], object_id, True, sequence_id)


async def _status_deleted(object_id, payload, sequence_id) -> None:
    if _is_actor_self_delete(payload["activity"]):
        return
    await _apply_status(payload["username"], _status_id(payload["activity"]), False, sequence_id)


handle_statuses_events, _, _ = \
    build_projection(topic=activities,
                     subscriber="person_account_statuses",
                     init=_noop,
                     on_snapshot_item=_noop_item,
                     on_message_type={"Create": _status_created,
                                      "Announce": _status_announced,
                                      "Delete": _status_deleted},
                     event_handler_signature=with_sequence_id)

