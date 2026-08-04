# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

from profed.models.activity_pub.activity_streams import ActivityStreamsObject


def _object_version(obj):
    return obj.get("updated") or obj.get("published")


def _sought(reference):
    return _object_version(reference.embedded) if reference.embedded else None


def _as_url(value):
    return value["id"] if isinstance(value, dict) else value


def _flattened(activity, event_type):
    obj = activity.get("object")
    return ({**activity, "object": _as_url(obj)}
            if event_type == "Announce" else
            {**activity, "object": {**obj, "inReplyTo": _as_url(obj["inReplyTo"])}}
            if isinstance(obj, dict) and isinstance(obj.get("inReplyTo"), dict) else
            activity)


def flatten_references(activity: dict, object_id, event_type, emitted_at, sign, enqueue) -> dict:
    for reference in ActivityStreamsObject.from_payload(object_id, event_type, activity).referenced_objects():
        enqueue(reference.url, reference.referrer, _sought(reference), emitted_at, sign)
    return _flattened(activity, event_type)

