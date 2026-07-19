# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import logging
import uuid
from profed.core.message_bus import message_bus
from profed.core.persistence.projections import (build_projection,
                                                 with_event_type,
                                                 with_emitted_at)
from profed.topics import activities
from profed.identity import acct_from_username
from profed.federation.webfinger import lookup_acct
from profed.util import noop
from .projections import recipients_at
from .storage import storage


logger = logging.getLogger(__name__)


def _follow_target(activity: dict) -> str | None:
    obj = activity.get("object")
    return obj if isinstance(obj, str) else None


def _accept_target(activity: dict) -> str | None:
    obj = activity.get("object")
    return obj.get("actor") if isinstance(obj, dict) else None


def _undo_target(activity: dict) -> str | None:
    obj = activity.get("object")
    inner = obj.get("object") if isinstance(obj, dict) else None
    return inner if isinstance(inner, str) else None


def _inner_object_url(activity: dict) -> str | None:
    obj = activity.get("object")
    return (obj
            if isinstance(obj, str) else
            obj.get("id")
            if isinstance(obj, dict) else
            None)


async def _mentioned_accts(activity: dict) -> set[str]:
    obj = activity.get("object")
    if not isinstance(obj, dict):
        return set()

    accts = {await lookup_acct(url)
             for url in {tag["href"]
                         for tag in obj.get("tag", [])
                         if isinstance(tag, dict) and
                            tag.get("type") == "Mention" and
                            tag.get("href")}}

    return {acct for acct in accts if acct}


async def _directed_recipients(target, activity: dict) -> set[str]:
    actor_url = target(activity)
    acct = await lookup_acct(actor_url) if actor_url else None
    return {acct} if acct else set()


async def _followers_and_mentions(activity: dict, username: str, emitted_at) -> set[str]:
    return (await recipients_at(acct_from_username(username), emitted_at) |
            await _mentioned_accts(activity))


async def _create_recipients(object_url: str, activity: dict, username: str, emitted_at) -> set[str]:
    return await _followers_and_mentions(activity, username, emitted_at)


async def _update_recipients(object_url: str, activity: dict, username: str, emitted_at) -> set[str]:
    return (await (await storage()).get_recipients(object_url) |
            await _followers_and_mentions(activity, username, emitted_at))


async def _delete_recipients(object_url: str, activity: dict, username: str, emitted_at) -> set[str]:
    return await (await storage()).get_recipients(object_url)


async def _store(object_url: str, recipients: set[str]) -> None:
    await (await storage()).put_recipients(object_url, recipients)


async def _forget(object_url: str, recipients: set[str]) -> None:
    await (await storage()).drop_recipients(object_url)


async def _publish_deliveries(object_id, activity, username, recipients) -> None:
    deliveries = message_bus().topic("deliveries", lookup_message_ids=True)
    for recipient in recipients:
        message_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{object_id}#{recipient}#queued")
        if not await deliveries.exists(message_id):
            async with deliveries.publish() as publish:
                await publish(event_type="queued",
                              object_id=f"{object_id}|{recipient}",
                              payload={"username": username, "activity": activity},
                              message_id=message_id)


def _object_fan_out(collect_recipients, persist):
    async def _fan_out(event_type, object_id, payload, emitted_at) -> None:
        activity = {"id": object_id, "type": event_type, **payload["activity"]}
        username = payload["username"]
        object_url = _inner_object_url(activity)
        recipients = await collect_recipients(object_url, activity, username, emitted_at)

        await asyncio.gather(persist(object_url, recipients),
                             _publish_deliveries(object_id, activity, username, recipients))
    return _fan_out


def _directed_fan_out(target):
    async def _fan_out(event_type, object_id, payload, emitted_at) -> None:
        activity = {"id": object_id, "type": event_type, **payload["activity"]}
        recipients = await _directed_recipients(target, activity)

        await _publish_deliveries(object_id, activity, payload["username"], recipients)
    return _fan_out


_create = _object_fan_out(_create_recipients, _store)
_update = _object_fan_out(_update_recipients, _store)
_delete = _object_fan_out(_delete_recipients, _forget)
_follow = _directed_fan_out(_follow_target)
_accept = _directed_fan_out(_accept_target)
_undo = _directed_fan_out(_undo_target)


handle_events, rebuild, _ = build_projection(topic=activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"Create": _create,
                                                              "Update": _update,
                                                              "Delete": _delete,
                                                              "Follow": _follow,
                                                              "Accept": _accept,
                                                              "Reject": _accept,
                                                              "Undo": _undo},
                                             event_handler_signature=(with_event_type & with_emitted_at))

