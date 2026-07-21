# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed import mentions
from profed.core.message_bus import message_bus
from profed.core.message_bus.source_key import source_key
from profed.core.persistence.projections import build_projection, with_event_type, with_sequence_id
from profed.sanitize import as2_html_fields, sanitize_as_object
from profed.topics import raw_activities
from profed.topics.activities_topic import ACTIVITIES_VERBS
from profed.util import noop
from .lookup import lookup


_RAW_ACTIVITIES_SOURCE = source_key("raw_activities")
_resolve_one = mentions.resolver(lookup)
_TRANSFORM_VERBS = {"Create", "Update"}


async def _forward(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    async with message_bus().topic("activities").publish() as publish:
        await publish(event_type=event_type,
                      object_id=object_id,
                      payload=payload,
                      message_id=_RAW_ACTIVITIES_SOURCE.message_id(sequence_id))


async def _polish_and_forward(event_type: str, object_id: str, payload: dict, sequence_id: int) -> None:
    activity = payload.get("activity")
    if not isinstance(activity, dict):
        await _forward(event_type, object_id, payload, sequence_id)
        return

    def set_tag_and_cc(a, obj, tag, cc):
        if isinstance(obj, dict):
            obj["tag"], obj["cc"] = tag, cc
        return {**a, "cc": cc or None}

    async def resolve_and_linkify(a):
        r = await mentions.resolve_all("\n".join(mentions.collect_html_texts(a, as2_html_fields)), _resolve_one)
        return mentions.linkify_document(a, r, as2_html_fields), r

    def resanitize(a, r):
        return sanitize_as_object(set_tag_and_cc(a, a.get("object"), *mentions.tag_cc(r)))

    await _forward(event_type,
                   object_id,
                   {**payload,
                    "activity": resanitize(*(await resolve_and_linkify(activity)))},
                   sequence_id)


handle_events, rebuild, _ = build_projection(topic=raw_activities,
                                             init=noop,
                                             on_snapshot_item=noop,
                                             on_message_type={verb: (_polish_and_forward
                                                                     if verb in _TRANSFORM_VERBS else
                                                                     _forward)
                                                              for verb in ACTIVITIES_VERBS},
                                             event_handler_signature=with_event_type & with_sequence_id)

