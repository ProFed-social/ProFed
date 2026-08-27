# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

_PUBLIC = "https://www.w3.org/ns/activitystreams#Public"

_ACTOR_OBJECT_VERBS = ("Follow", "Block", "Accept", "Reject", "Undo")


def _as_url(value):
    return (value if isinstance(value, str) else
            value.get("id") if isinstance(value, dict) else
            None)


def _audience(part: dict):
    return (url
            for key in ("to", "cc")
            for url in (part.get(key) or [])
            if url != _PUBLIC and not url.endswith("/followers"))


def _mention_hrefs(part: dict):
    return (tag.get("href")
            for tag in (part.get("tag") or [])
            if isinstance(tag, dict) and tag.get("type") == "Mention")


def _mention_names(part: dict):
    return (tag.get("name")
            for tag in (part.get("tag") or [])
            if isinstance(tag, dict) and tag.get("type") == "Mention")


def _object_urls(activity: dict):
    obj = activity.get("object")
    inner = obj.get("object") if isinstance(obj, dict) else None

    yield _as_url(activity.get("actor"))
    yield obj.get("attributedTo") if isinstance(obj, dict) else None
    yield obj if isinstance(obj, str) and activity.get("type") in _ACTOR_OBJECT_VERBS else None
    yield inner if isinstance(inner, str) and activity.get("type") == "Undo" else None


def actor_urls(activity: dict) -> set[str]:
    obj = activity.get("object")
    parts = (activity, obj if isinstance(obj, dict) else {})

    return {url
            for url in (list(_object_urls(activity)) +
                        [href for part in parts for href in _mention_hrefs(part)] +
                        [url for part in parts for url in _audience(part)])
            if isinstance(url, str) and url.startswith("https://")}


def accts(activity: dict) -> set[str]:
    obj = activity.get("object")
    parts = (activity, obj if isinstance(obj, dict) else {})

    return {name.lstrip("@")
            for part in parts
            for name in _mention_names(part)
            if isinstance(name, str) and "@" in name.lstrip("@")}

