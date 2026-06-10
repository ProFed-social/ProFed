# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_sequence_id
from profed.topics import person, followers, activities
from profed.identity import acct_from_username, account_id, username_from_acct
from profed.models.mastodon import Account
from .storage import storage


logger = logging.getLogger(__name__)
_PERSON_SOURCE     = source_key("person")
_FOLLOWERS_SOURCE  = source_key("followers")
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
    account = Account.from_actor(person_actor,
                                 acct=acct,
                                 account_id=account_id(acct),
                                 url=person_actor["id"])

    published = person_actor.get("published")
    if published:
        account.created_at = published

    counts = await (await storage()).get(username)
    account.followers_count = counts["followers"]
    account.following_count = counts["following"]
    account.statuses_count  = counts["statuses"]

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


async def _bump_followers(object_id: str, delta: int, sequence_id: int) -> None:
    username = username_from_acct(object_id.split("|", 1)[1])
    count = await (await storage()).bump(username, "followers", delta)
    await _emit_count("followers_changed", username, count, _FOLLOWERS_SOURCE, sequence_id)


async def _follower_created(object_id, payload, sequence_id) -> None:
    await _bump_followers(object_id, 1, sequence_id)


async def _follower_deleted(object_id, payload, sequence_id) -> None:
    await _bump_followers(object_id, -1, sequence_id)


handle_followers_events, _, _ = \
    build_projection(topic=followers,
                     subscriber="person_account_followers",
                     init=_noop,
                     on_snapshot_item=_noop_item,
                     on_message_type={"created": _follower_created,
                                      "deleted": _follower_deleted},
                     event_handler_signature=with_sequence_id)


def _is_actor_object(activity: dict) -> bool:
    obj = activity.get("object")
    return isinstance(obj, dict) and obj.get("type") in _ACTOR_TYPES


def _is_actor_self_delete(activity: dict) -> bool:
    return activity.get("actor") is not None and activity.get("actor") == activity.get("object")


async def _bump_statuses(username: str, delta: int, sequence_id: int) -> None:
    count = await (await storage()).bump(username, "statuses", delta)
    await _emit_count("statuses_changed", username, count, _ACTIVITIES_SOURCE, sequence_id)


async def _status_created(object_id, payload, sequence_id) -> None:
    if _is_actor_object(payload["activity"]):
        return
    await _bump_statuses(payload["username"], 1, sequence_id)


async def _status_announced(object_id, payload, sequence_id) -> None:
    await _bump_statuses(payload["username"], 1, sequence_id)


async def _status_deleted(object_id, payload, sequence_id) -> None:
    if _is_actor_self_delete(payload["activity"]):
        return
    await _bump_statuses(payload["username"], -1, sequence_id)


handle_statuses_events, _, _ = \
    build_projection(topic=activities,
                     subscriber="person_account_statuses",
                     init=_noop,
                     on_snapshot_item=_noop_item,
                     on_message_type={"Create":   _status_created,
                                      "Announce": _status_announced,
                                      "Delete":   _status_deleted},
                     event_handler_signature=with_sequence_id)

