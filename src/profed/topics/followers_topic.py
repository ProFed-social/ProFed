# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


_EVENT_VERBS = ("requested", "accepted", "rejected", "deleted")
_EDGE_STATES = ("requested", "accepted")


def _ignore(msg):
    return f"Ignoring malformed followers event: {msg}"


def validate_followers_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _EVENT_VERBS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None

    return payload

def validate_followers_snapshot_item(item) -> Optional[Dict]:
    if not isinstance(item, dict):
        return None

    for key in ("follower", "following"):
        val = item.get(key)
        if not isinstance(val, str) or not val:
            return None

    state = item.get("state")
    if state is not None and state not in _EDGE_STATES:
        return None

    return item


topic = {"name":              "followers",
         "validate":          validate_followers_event,
         "snapshot_validate": validate_followers_snapshot_item}

