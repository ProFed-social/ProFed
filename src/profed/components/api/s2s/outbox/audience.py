# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

PUBLIC = "https://www.w3.org/ns/activitystreams#Public"

PUBLIC_VISIBILITY = "public"

FOLLOWERS_VISIBILITY = "followers"

DIRECT_VISIBILITY = "direct"


def _parts(activity: dict) -> list[dict]:
    inner = activity.get("object")
    return [activity] + ([inner] if isinstance(inner, dict) else [])


def _audience(activity: dict) -> set[str]:
    return {url
            for part in _parts(activity)
            for key in ("to", "cc")
            for url in (part.get(key) or [])}


def _author(activity: dict) -> str:
    inner = activity.get("object")
    return (activity.get("actor")
            or (inner.get("attributedTo") if isinstance(inner, dict) else None)
            or "")


def visibility_of(activity: dict) -> str:
    audience = _audience(activity)
    return (PUBLIC_VISIBILITY
            if PUBLIC in audience else
            FOLLOWERS_VISIBILITY
            if f"{_author(activity)}/followers" in audience else
            DIRECT_VISIBILITY)


def recipients_of(activity: dict) -> list[str]:
    return sorted({url
                   for url in _audience(activity)
                   if url != PUBLIC and not url.endswith("/followers")})

