# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict
from profed.core.message_bus import message_bus


logger = logging.getLogger(__name__)


_EVENT_VERBS = ("added", "removed")


def _ignore(msg):
    return f"Ignoring malformed bookmarks event: {msg}"


def _named(payload: Dict, key: str) -> Optional[str]:
    value = payload.get(key)
    return value if isinstance(value, str) and value else None


def bookmark_id(username: str, object_url: str) -> str:
    return f"{username}|{object_url}"


def validate_bookmarks_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _EVENT_VERBS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    if not all(_named(payload, key) for key in ("username", "object_url")):
        logger.warning(_ignore(f"no usable username and object_url: {payload!r}"))
        return None

    return payload


def validate_bookmarks_snapshot_item(item) -> Optional[Dict]:
    return (item
            if isinstance(item, dict) and all(_named(item, key) for key in ("username", "object_url")) else
            None)


async def publish_bookmark(event_type: str, username: str, object_url: str) -> None:
    async with message_bus().topic("bookmarks").publish() as publish:
        await publish(event_type=event_type,
                      object_id=bookmark_id(username, object_url),
                      payload={"username": username, "object_url": object_url})


topic = {"name":              "bookmarks",
         "validate":          validate_bookmarks_event,
         "snapshot_validate": validate_bookmarks_snapshot_item}

