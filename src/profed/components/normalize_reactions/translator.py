# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import (build_projection,
                                                 with_emitted_at,
                                                 with_event_type,
                                                 with_sequence_id)
from profed.emoji import is_emoji
from profed.identity import is_local_actor_url
from profed.topics import incoming_activities
from profed.topics.incoming_activities_topic import is_reaction
from profed.topics.known_servers_topic import host_of
from profed.topics.unknown_actors_topic import throttled_id
from profed.util import noop


_SOURCE = source_key("incoming_activities")

_DROPPED = ("content", "_misskey_reaction")


def _emoji(activity: dict) -> str:
    candidate = activity.get("content") or activity.get("_misskey_reaction") or ""
    return candidate if is_emoji(candidate) else ""


def as_like(activity: dict) -> dict:
    emoji = _emoji(activity)
    return {**{key: value for key, value in activity.items() if key not in _DROPPED},
            "type": "Like",
            **({"content": emoji} if emoji else {})}


def normalized(event_type: str, activity: dict) -> dict:
    return ({**activity, "object": as_like(activity["object"])}
            if event_type == "Undo" else
            as_like(activity))


async def observe(event_type: str, activity: dict, emitted_at) -> None:
    actor = activity.get("actor") or ""
    host = "" if event_type != "EmojiReact" or is_local_actor_url(actor) else host_of(actor)
    if not host:
        return

    async with message_bus().topic("known_servers").publish() as publish:
        await publish(event_type="observed",
                      object_id=host,
                      payload={"activity_type": event_type, "observed_at": emitted_at.isoformat()},
                      message_id=throttled_id("reactions", host))


async def _forward(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    topic = message_bus().topic("resolved_activities", lookup_message_ids=True)
    message_id = _SOURCE.message_id(sequence_id)
    if not await topic.exists(message_id):
        async with topic.publish() as publish:
            await publish(event_type="Like" if event_type != "Undo" else "Undo",
                          object_id=object_id,
                          payload={**payload, "activity": normalized(event_type, payload["activity"])},
                          message_id=message_id)


async def _handle(event_type: str, object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    if not is_reaction(event_type, payload["activity"]):
        return

    await _forward(event_type, object_id, payload, sequence_id)
    await observe(event_type, payload["activity"], emitted_at)


handle_events, rebuild, _ = build_projection(topic=incoming_activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={"Like": _handle,
                                                              "EmojiReact": _handle,
                                                              "Undo": _handle},
                                             event_handler_signature=(with_event_type &
                                                                      with_emitted_at &
                                                                      with_sequence_id))

