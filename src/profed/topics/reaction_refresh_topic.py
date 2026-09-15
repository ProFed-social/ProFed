# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict
from profed.core.message_bus import message_bus


logger = logging.getLogger(__name__)


_EVENT_VERBS = ("requested",)


def _ignore(msg):
    return f"Ignoring malformed reaction_refresh event: {msg}"


def _urls_of(payload: Dict) -> Optional[list]:
    listed = payload.get("object_urls")
    return (None
            if not isinstance(listed, list) else
            list(dict.fromkeys(url for url in listed if isinstance(url, str) and url)) or None)


def validate_reaction_refresh_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _EVENT_VERBS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    urls = _urls_of(payload)
    if urls is None:
        logger.warning(_ignore(f"no usable object_urls: {payload.get('object_urls')!r}"))
        return None

    return {**payload, "object_urls": urls}


def validate_reaction_refresh_snapshot_item(item) -> Optional[Dict]:
    return None


async def publish_refresh(object_urls: list, message_id=None) -> None:
    urls = list(dict.fromkeys(url for url in object_urls if url))
    if not urls:
        return

    async with message_bus().topic("reaction_refresh").publish() as publish:
        await publish(event_type="requested",
                      object_id=urls[0],
                      payload={"object_urls": urls},
                      message_id=message_id)


topic = {"name":              "reaction_refresh",
         "validate":          validate_reaction_refresh_event,
         "snapshot_validate": validate_reaction_refresh_snapshot_item}

