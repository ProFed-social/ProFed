# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_event_type, with_sequence_id
from profed.identity import acct_from_username
from profed.topics import incoming_activities, person, raw_activities, remote_actors
from profed.topics.incoming_activities_topic import _KNOWN_VERBS
from profed.util import noop
from . import extract, storage


logger = logging.getLogger(__name__)


async def _publish(event_type: str, names, source: str, sequence_id: int) -> None:
    async with message_bus().topic("unknown_actors").publish() as publish:
        for name in sorted(names):
            await publish(event_type=event_type,
                          object_id=name,
                          payload={},
                          message_id=source_key(f"{source}|{name}").message_id(sequence_id))


async def _report(activity: dict, source: str, sequence_id: int) -> None:
    store = await storage.storage()
    await _publish("discovered_url",
                   await store.unknown_urls(sorted(extract.actor_urls(activity))),
                   source,
                   sequence_id)
    await _publish("discovered_acct",
                   await store.unknown_accts(sorted(extract.accts(activity))),
                   source,
                   sequence_id)


def _reporter(source: str):
    async def _handle(event_type, object_id, payload, sequence_id) -> None:
        await _report({"id": object_id, "type": event_type, **(payload.get("activity") or {})},
                      source,
                      sequence_id)

    return _handle


def _on_every_verb(source: str):
    return {verb: _reporter(source) for verb in _KNOWN_VERBS}


async def _remote_discovered(object_id, payload) -> None:
    await (await storage.storage()).upsert(payload["actor_url"], payload.get("acct"))


async def _person_changed(object_id, payload) -> None:
    await (await storage.storage()).upsert(payload["id"], acct_from_username(object_id))


async def _person_deleted(object_id, payload) -> None:
    await (await storage.storage()).delete(payload["id"])


remote_actors_handle_events, remote_actors_rebuild, _ = \
    build_projection(topic=remote_actors,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={"discovered": _remote_discovered})

person_handle_events, person_rebuild, _ = \
    build_projection(topic=person,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type={"created": _person_changed,
                                      "updated": _person_changed,
                                      "deleted": _person_deleted})

incoming_handle_events, _, _ = \
    build_projection(topic=incoming_activities,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type=_on_every_verb("incoming_activities"),
                     event_handler_signature=with_event_type & with_sequence_id)

raw_handle_events, _, _ = \
    build_projection(topic=raw_activities,
                     init=noop,
                     on_snapshot_item=noop,
                     on_message_type=_on_every_verb("raw_activities"),
                     event_handler_signature=with_event_type & with_sequence_id)

