# Copyright (C) 2026 Christof Donat
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging
from typing import Optional, Dict


logger = logging.getLogger(__name__)


_KNOWN_VERBS = {"Create",
                "Update",
                "Delete",
                "Follow",
                "Accept",
                "Reject",
                "Undo",
                "Like",
                "Announce",
                "Block"}


def _ignore(msg):
    return f"Ignoring malformed incoming_activities event: {msg}"


def validate_incoming_activities_event(event_type: str, payload: Dict) -> Optional[Dict]:
    if event_type not in _KNOWN_VERBS:
        logger.warning(_ignore(f"unknown event type {event_type!r}"))
        return None

    if not isinstance(payload, dict):
        logger.warning(_ignore(f"payload not a dict: {payload!r}"))
        return None
    
    if not isinstance(payload.get("username"), str) or not payload["username"]:
        logger.warning(_ignore(f"missing or invalid username: {payload!r}"))
        return None

    if not isinstance(payload.get("activity"), dict):
        logger.warning(_ignore(f"missing or invalid activity: {payload!r}"))
        return None

    return payload


def validate_incoming_activities_snapshot_item(item) -> Optional[Dict]:
    return None


topic = {"name":              "incoming_activities",
         "validate":          validate_incoming_activities_event,
         "snapshot_validate": validate_incoming_activities_snapshot_item}

