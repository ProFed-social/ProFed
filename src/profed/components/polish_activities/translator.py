# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import uuid
from profed import mentions
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_emitted_at, with_event_type, with_sequence_id
from profed.identity import is_local
from profed.sanitize import as2_html_fields, sanitize_as_object
from profed.topics import raw_activities
from profed.topics.activities_topic import ACTIVITIES_VERBS
from profed.util import noop
from .storage import storage


_RAW_ACTIVITIES_SOURCE = source_key("raw_activities")
_TRANSFORM_VERBS = {"Create", "Update"}
_UNFINISHED_VERBS = {"Create", "Update"}


async def lookup(acct: str) -> str | None:
    return await (await storage()).url_for(acct)


_resolve_one = mentions.resolver(lookup)


def _merge_tag(existing, added):
    added_hrefs = {mention["href"] for mention in added}
    kept = [entry for entry in existing if not (isinstance(entry, dict) and entry.get("href") in added_hrefs)]
    return kept + added


def _merge_cc(existing, added):
    return existing + [url for url in added if url not in existing]


def _object_url(activity: dict) -> str | None:
    obj = activity.get("object")
    return (obj.get("id") if isinstance(obj, dict) else obj) if obj is not None else None


def unresolved_accts(resolved) -> list[str]:
    return sorted({acct for _, _, acct, url in resolved if url is None and not is_local(acct)})


def set_tag_and_cc(activity, obj, tag, cc):
    if isinstance(obj, dict):
        obj["tag"] = _merge_tag(obj.get("tag") or [], tag)
        obj["cc"] = _merge_cc(obj.get("cc") or [], cc)
        cc = obj["cc"]

    return {**activity, "cc": cc or None}


async def polish(activity: dict) -> tuple[dict, list[str]]:
    resolved = await mentions.resolve_all("\n".join(mentions.collect_html_texts(activity, as2_html_fields)),
                                          _resolve_one)
    linkified = mentions.linkify_document(activity, resolved, as2_html_fields)

    return (sanitize_as_object(set_tag_and_cc(linkified, linkified.get("object"), *mentions.tag_cc(resolved))),
            unresolved_accts(resolved))


async def _publish(event_type: str, object_id: str, payload: dict, message_id) -> None:
    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=message_id)


async def _request_resolution(accts) -> None:
    async with message_bus().topic("unknown_actors").publish() as publish:
        for acct in accts:
            await publish(event_type="discovered_acct",
                          object_id=acct,
                          payload={},
                          message_id=uuid.uuid5(uuid.NAMESPACE_URL, f"polish_activities#{acct}"))


async def _forward(event_type: str, object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    await _publish(event_type, object_id, payload, _RAW_ACTIVITIES_SOURCE.message_id(sequence_id))


async def _polish_and_forward(event_type: str, object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity = payload.get("activity")
    if not isinstance(activity, dict):
        await _forward(event_type, object_id, payload, emitted_at, sequence_id)
        return

    await publish_polished(event_type,
                           object_id,
                           payload,
                           emitted_at,
                           _RAW_ACTIVITIES_SOURCE.message_id(sequence_id))


async def remember_pending(event_type, object_id, payload, emitted_at, pending) -> None:
    url = _object_url(payload["activity"])
    if url is None:
        return

    await (await storage()).release(url)
    if pending and event_type in _UNFINISHED_VERBS:
        await (await storage()).hold(url, event_type, object_id, json.dumps(payload), emitted_at, pending)
        await _request_resolution(pending)


async def publish_polished(event_type, object_id, payload, emitted_at, message_id) -> None:
    polished, pending = await polish(payload["activity"])
    await remember_pending(event_type, object_id, payload, emitted_at, pending)
    await _publish(event_type, object_id, {**payload, "activity": polished}, message_id)


async def _deleted(event_type: str, object_id: str, payload: dict, emitted_at, sequence_id: int) -> None:
    activity = payload.get("activity")
    url = _object_url(activity) if isinstance(activity, dict) else None
    if url is not None:
        await (await storage()).release(url)

    await _forward(event_type, object_id, payload, emitted_at, sequence_id)


handle_events, rebuild, _ = build_projection(topic=raw_activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: (_polish_and_forward
                                                                     if verb in _TRANSFORM_VERBS else
                                                                     _deleted
                                                                     if verb == "Delete" else
                                                                     _forward)
                                                              for verb in ACTIVITIES_VERBS},
                                             event_handler_signature=(with_event_type
                                                                      & with_emitted_at
                                                                      & with_sequence_id))

