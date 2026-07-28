# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from asyncio import gather
from profed.federation.objects import fetch_object
from profed.models.activity_pub.activity_streams import ActivityStreamsObject
from profed.sanitize import sanitize_as_object
from profed.topics.incoming_activities_topic import publish_incoming


async def _object_of(reference, sign):
    return (reference.embedded
            if reference.embedded is not None else
            sanitize_as_object(await fetch_object(reference.url, sign)))


async def _feed_back(reference, sign) -> None:
    obj = await _object_of(reference, sign)
    return (None
            if obj is None else
            await publish_incoming("Update", reference.url, "",
                                   {"actor": obj.get("attributedTo"), "object": obj}))


def _as_url(value):
    return value["id"] if isinstance(value, dict) else value


def _flattened(activity):
    obj = activity.get("object")
    return ({**activity, "object": _as_url(obj)}
            if activity.get("type") == "Announce" else
            {**activity, "object": {**obj, "inReplyTo": _as_url(obj["inReplyTo"])}}
            if isinstance(obj, dict) and isinstance(obj.get("inReplyTo"), dict) else
            activity)


async def flatten_references(activity: dict, sign=None) -> dict:
    references = ActivityStreamsObject.model_validate(activity).referenced_objects()
    await gather(*(_feed_back(reference, sign) for reference in references))
    return _flattened(activity)

